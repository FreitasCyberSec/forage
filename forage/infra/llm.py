"""LLM routing with direct Groq structured outputs and LiteLLM fallback."""

import time
from dataclasses import dataclass

import httpx
import litellm

from forage.infra.config import NerfedConfig, ProviderConfig
from forage.safety.audit import AuditLog

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True

TIER_ORDER = ["routine", "important", "complex", "critical"]
GROQ_DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


class LLMRouter:
    def __init__(self, config: NerfedConfig, audit: AuditLog):
        self.config = config
        self.audit = audit
        self._providers_by_tier: dict[str, list[ProviderConfig]] = {}
        self._setup_providers()

    def _setup_providers(self) -> None:
        """Group providers by tier."""
        for p in self.config.providers:
            self._providers_by_tier.setdefault(p.tier, []).append(p)

            if p.api_key:
                key_env_map = {
                    "groq": "GROQ_API_KEY",
                    "openai": "OPENAI_API_KEY",
                    "anthropic": "ANTHROPIC_API_KEY",
                    "deepseek": "DEEPSEEK_API_KEY",
                    "together": "TOGETHER_API_KEY",
                }
                import os

                env_key = key_env_map.get(p.name)
                if env_key and p.api_key:
                    os.environ.setdefault(env_key, p.api_key)

    def _get_provider_for_tier(self, tier: str) -> tuple[ProviderConfig, str] | None:
        """Get the first available provider for a tier, with fallback up then down."""
        tier_idx = TIER_ORDER.index(tier) if tier in TIER_ORDER else 0
        search_order = TIER_ORDER[tier_idx:] + list(reversed(TIER_ORDER[:tier_idx]))

        for t in search_order:
            providers = self._providers_by_tier.get(t, [])
            if providers:
                p = providers[0]
                model = p.models[0] if p.models else "gpt-4o-mini"

                if p.name == "ollama":
                    model_str = f"ollama/{model}"
                elif p.name == "openai":
                    model_str = model
                else:
                    model_str = f"{p.name}/{model}"

                return p, model_str

        return None

    def _calculate_cost(self, model_str: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate actual call cost from LiteLLM's model price table."""
        try:
            model_info = litellm.model_cost.get(model_str, {})
            input_cost = model_info.get("input_cost_per_token", 0.000001)
            output_cost = model_info.get("output_cost_per_token", 0.000002)
            return input_tokens * input_cost + output_tokens * output_cost
        except Exception:
            return (input_tokens * 0.001 + output_tokens * 0.002) / 1000

    def _complete_groq_structured(
        self,
        *,
        provider: ProviderConfig,
        messages: list[dict],
        tier: str,
        max_tokens: int,
        temperature: float,
        json_schema: dict,
        json_schema_name: str,
        json_schema_strict: bool,
    ) -> LLMResponse:
        """Call Groq directly for strict JSON Schema output.

        This intentionally bypasses LiteLLM for Groq structured outputs because
        provider translation can fall back to JSON Object Mode and trigger
        json_validate_failed errors before the response reaches the agent.
        """
        if not provider.api_key:
            raise RuntimeError("Groq API key is missing")

        if not provider.models:
            raise RuntimeError("Groq provider has no model configured")

        raw_model = provider.models[0]
        model_str = f"groq/{raw_model}"

        base_url = (provider.base_url or GROQ_DEFAULT_BASE_URL).rstrip("/")
        if base_url.endswith("/chat/completions"):
            endpoint = base_url
        else:
            endpoint = f"{base_url}/chat/completions"

        payload = {
            "model": raw_model,
            "messages": messages,
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": json_schema_name,
                    "strict": json_schema_strict,
                    "schema": json_schema,
                },
            },
        }

        # GPT-OSS models reason by default. Keep reasoning hidden so only the
        # schema-constrained JSON is returned in message.content.
        if raw_model.startswith("openai/gpt-oss-"):
            payload["reasoning_effort"] = "low"
            payload["reasoning_format"] = "hidden"

        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }

        start = time.time()

        try:
            response = httpx.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            details = {
                "model": raw_model,
                "tier": tier,
                "provider": "groq-direct",
            }
            if "response" in locals():
                details["response"] = response.text[:1000]

            self.audit.log(
                "llm_error",
                f"Direct Groq structured call failed: {e}",
                level="error",
                details=details,
            )
            raise

        latency_ms = (time.time() - start) * 1000

        try:
            content = data["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected Groq response shape: {data}") from e

        usage = data.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens", 0) or 0)
        output_tokens = int(usage.get("completion_tokens", 0) or 0)
        cost = self._calculate_cost(model_str, input_tokens, output_tokens)

        self.audit.log(
            "llm_call",
            f"LLM: {model_str} ({tier}, direct structured)",
            cost_usd=cost,
            details={
                "model": raw_model,
                "tier": tier,
                "provider": "groq-direct",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": round(latency_ms, 1),
            },
        )

        return LLMResponse(
            content=content,
            model=model_str,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
        )

    def complete(
        self,
        prompt: str,
        *,
        tier: str = "routine",
        system: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        json_mode: bool = False,
        json_schema: dict | None = None,
        json_schema_name: str = "response",
        json_schema_strict: bool = True,
    ) -> LLMResponse:
        """Call the selected LLM with tier-based routing and cost tracking."""
        result = self._get_provider_for_tier(tier)
        if not result:
            raise RuntimeError(f"No LLM provider available for tier '{tier}' or above")

        provider, model_str = result

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # For Groq + JSON Schema, bypass LiteLLM and call Groq directly.
        if provider.name == "groq" and json_schema is not None:
            return self._complete_groq_structured(
                provider=provider,
                messages=messages,
                tier=tier,
                max_tokens=max_tokens,
                temperature=temperature,
                json_schema=json_schema,
                json_schema_name=json_schema_name,
                json_schema_strict=json_schema_strict,
            )

        kwargs = {
            "model": model_str,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if provider.base_url:
            kwargs["api_base"] = provider.base_url

        if json_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": json_schema_name,
                    "strict": json_schema_strict,
                    "schema": json_schema,
                },
            }
        elif json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        start = time.time()

        try:
            response = litellm.completion(**kwargs)
        except Exception as e:
            self.audit.log(
                "llm_error",
                f"LLM call failed: {e}",
                level="error",
                details={"model": model_str, "tier": tier},
            )
            raise

        latency_ms = (time.time() - start) * 1000
        content = response.choices[0].message.content or ""
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        try:
            cost = litellm.completion_cost(completion_response=response)
        except Exception:
            cost = self._calculate_cost(model_str, input_tokens, output_tokens)

        self.audit.log(
            "llm_call",
            f"LLM: {model_str} ({tier})",
            cost_usd=cost,
            details={
                "model": model_str,
                "tier": tier,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": round(latency_ms, 1),
            },
        )

        return LLMResponse(
            content=content,
            model=model_str,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
        )

    def estimate_cost(
        self,
        tier: str,
        input_tokens: int = 1000,
        output_tokens: int = 500,
    ) -> float:
        """Estimate cost without making a call."""
        result = self._get_provider_for_tier(tier)
        if not result:
            return 0.01

        _, model_str = result
        return self._calculate_cost(model_str, input_tokens, output_tokens)
