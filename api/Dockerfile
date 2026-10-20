# StudyMate API image (CPU only). Build from the repository root:
#   docker build -f api/Dockerfile -t studymate-api .
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# torch first, from the CPU index (the PyPI Linux wheel pulls CUDA), then the lock.
COPY requirements.txt .
RUN pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

# Bake the embedding model into the image: no download when the container starts.
# HF_HOME is shared: the model is downloaded as root but read by the non-root user.
ARG EMBEDDING_MODEL=intfloat/multilingual-e5-small
ENV EMBEDDING_MODEL=${EMBEDDING_MODEL} \
    HF_HOME=/opt/hf
RUN python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['EMBEDDING_MODEL'])" \
    && chmod -R a+rX /opt/hf
ENV HF_HUB_OFFLINE=1

COPY config.py ./
COPY agent/ agent/
COPY api/ api/
COPY course/ course/
COPY rag/ rag/
COPY scripts/ scripts/

# Non-root user.
RUN useradd --create-home studymate
USER studymate

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
