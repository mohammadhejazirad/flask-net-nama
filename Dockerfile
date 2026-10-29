FROM node:24-bookworm-slim@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend ./frontend
COPY netnama/templates ./netnama/templates
RUN npm run build

FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb
# Build-only settings; optional overrides via docker compose build --build-arg.
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_DEFAULT_TIMEOUT=120
ARG PIP_RETRIES=5
ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NETNAMA_DATA_DIR=/data \
    NETNAMA_MODE=public NETNAMA_HOST=0.0.0.0 NETNAMA_PORT=8080
WORKDIR /app
RUN groupadd --gid 10001 netnama && useradd --uid 10001 --gid 10001 --no-create-home netnama \
    && mkdir /data && chown netnama:netnama /data
COPY requirements.lock /app/requirements.lock
RUN --mount=type=cache,id=netnama-pip,target=/root/.cache/pip,sharing=locked \
    for attempt in 1 2 3; do \
        python -m pip install --require-hashes -r requirements.lock && break; \
        if [ "$attempt" = 3 ]; then exit 1; fi; \
        echo "Dependency download failed; retrying ($attempt/3)..."; \
        sleep 5; \
    done
COPY pyproject.toml LICENSE THIRD_PARTY_NOTICES.md /app/
COPY docs/licenses /app/docs/licenses
COPY netnama /app/netnama
COPY --from=frontend /build/netnama/static/dist /app/netnama/static/dist
RUN --mount=type=cache,id=netnama-pip,target=/root/.cache/pip,sharing=locked \
    for attempt in 1 2 3; do \
        python -m pip install --no-deps . && break; \
        if [ "$attempt" = 3 ]; then exit 1; fi; \
        echo "Application build failed; retrying ($attempt/3)..."; \
        sleep 5; \
    done
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz',timeout=2)"
CMD ["python", "-m", "netnama"]
