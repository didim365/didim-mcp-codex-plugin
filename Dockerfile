# didim-mcp-codex-plugin — multi-stage build (React 정적 산출물 + FastAPI 런타임)
#
# **하나의 image, 하나의 container** 다(요구사항 §4 · §18 · §22). 별도 frontend Pod 을
# 만들지 않는다 — FastAPI 가 `/api/**` 와 React SPA 를 함께 낸다(app/web/spa.py).
#
# 기존 DIDIM 규약(didim-rag-backend / didim-mcp-service-frontend)을 그대로 따른다:
# python:3.12-slim + uv, node:22-slim 빌드, 비루트 실행(uid/gid 999), stdlib healthcheck,
# port 8080. 최종 image 에 build toolchain(node · uv · devDependencies)을 넣지 않는다.

# ── web-deps ──────────────────────────────────────────────
FROM node:22-slim AS web-deps
WORKDIR /build

# 사내망 TLS 검사(FortiGate) 대응. 없으면 `npm ci` 가 레지스트리 인증서를 믿지 못해
# SELF_SIGNED_CERT_IN_CHAIN 으로 죽는다 — 호스트에는 CA 가 깔려 있어 로컬 npm 은 멀쩡하므로
# 컨테이너에서만 드러난다.
#
# `update-ca-certificates` 를 쓰지 않는다 — node:22-slim 에는 ca-certificates 패키지가
# **없다**(python:3.12-slim 과 다른 점이다). node 는 NODE_EXTRA_CA_CERTS 하나만 본다.
COPY certs/ /etc/didim-ca/
RUN cat /etc/didim-ca/*.crt > /etc/didim-ca/bundle.crt 2>/dev/null || : >/etc/didim-ca/bundle.crt
ENV NODE_EXTRA_CA_CERTS=/etc/didim-ca/bundle.crt

# lockfile 이 그대로면 이 layer 는 캐시된다. `npm ci` 는 lock 을 재해석하지 않는다.
COPY web/package.json web/package-lock.json ./
RUN npm ci

# ── web-build ─────────────────────────────────────────────
FROM node:22-slim AS web-build
WORKDIR /build
COPY --from=web-deps /build/node_modules ./node_modules
COPY --from=web-deps /etc/didim-ca/bundle.crt /etc/didim-ca/bundle.crt
ENV NODE_EXTRA_CA_CERTS=/etc/didim-ca/bundle.crt
COPY web/ ./
# `npm run build` 는 `tsc --noEmit && vite build` 다 — 타입 오류가 이미지에 들어가지 않는다.
RUN npm run build

# ── api-builder ───────────────────────────────────────────
FROM python:3.12-slim AS api-builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /build
RUN uv venv /opt/venv

# 의존성 설치와 프로젝트 설치를 두 layer 로 나눈다 — 소스 한 줄 바꿀 때마다 전체 재설치를
# 하지 않기 위해서다.
# --frozen: uv.lock 을 재해석하지 않고 고정 버전 그대로. --no-dev: 개발 의존성 제외.
# 기존 Jenkins(legacy builder) 호환을 위해 BuildKit 전용 cache mount 는 쓰지 않는다.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY app ./app
RUN uv sync --frozen --no-dev

# ── runtime ───────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# 사내망 TLS 검사(FortiGate) 대응. 이 서비스는 Auth(JWKS · /me · login_code 교환)를
# HTTPS 로 부를 수 있으므로 런타임에도 CA 가 필요하다.
COPY certs/ /usr/local/share/ca-certificates/
RUN rm -f /usr/local/share/ca-certificates/README.md && update-ca-certificates

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    HOME=/app \
    # SPA 산출물 위치. app/core/config.py 의 기본값과 같지만, 이미지 안 경로를 명시해
    # 두는 편이 배포에서 덜 헷갈린다.
    DIDIM_SKILL_SPA_DIR=/app/web/dist

# uid/gid 를 **숫자로 고정**한다. Kubernetes 에서 `runAsNonRoot: true` 만 두고 이름 기반
# USER 를 쓰면 kubelet 이 Pod 을 거부한다(didim-rag-backend-deploy 에서 겪은 것).
RUN groupadd -r -g 999 app && useradd -r -u 999 -g app app

WORKDIR /app
COPY --from=api-builder /opt/venv /opt/venv
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
# React 정적 산출물만 가져온다 — node_modules 도 node 런타임도 이미지에 없다.
COPY --from=web-build /build/dist ./web/dist

RUN chown -R app:app /app
USER app

EXPOSE 8080

# curl 없는 slim 이미지 → stdlib 로 healthcheck.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3).status==200 else 1)"

# Alembic 은 여기서 돌리지 않는다 — migration 은 별도 Job 이다(요구사항 §20).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
