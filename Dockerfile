FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir .

RUN mkdir -p /data

ENV FORAGE_DATA_DIR=/data
ENV PYTHONUNBUFFERED=1

EXPOSE 3000

ENTRYPOINT ["forage"]
CMD ["start"]