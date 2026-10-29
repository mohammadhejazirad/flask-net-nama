FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NETNAMA_DATA_DIR=/data
WORKDIR /app
RUN groupadd --gid 10001 netnama && useradd --uid 10001 --gid 10001 --no-create-home netnama \
    && mkdir /data && chown netnama:netnama /data
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY pyproject.toml LICENSE THIRD_PARTY_NOTICES.md /app/
COPY docs/licenses /app/docs/licenses
COPY netnama /app/netnama
RUN pip install --no-cache-dir --no-deps .
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz',timeout=2)"
CMD ["python", "-m", "netnama"]
