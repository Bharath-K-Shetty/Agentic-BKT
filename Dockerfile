FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    HOMIE_STATE_DIR=/var/data/homie
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY webapp ./webapp
COPY research ./research
COPY data ./data
COPY docs ./docs
RUN mkdir -p /var/data/homie
EXPOSE 10000
CMD ["sh", "-c", "exec uvicorn webapp.backend.cloud:create_app --factory --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
