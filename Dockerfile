# 빌드: docker build -t mintmark-api .
# 실행: docker run -p 8000:8000 -e MINTMARK_SECRET_KEY=... mintmark-api

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# AWS Lambda Web Adapter 확장 추가 (컨테이너 이미지를 Lambda에서 HTTP로 실행)
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY api ./api
COPY core ./core
COPY cli ./cli

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir .

EXPOSE 8000

# Lambda Web Adapter가 uvicorn(8000)으로 트래픽을 전달하도록 포트 지정
ENV AWS_LWA_PORT=8000

# 프로덕션: 단일 워커, 호스트 0.0.0.0
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
