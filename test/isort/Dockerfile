# Dockerfile to apply isort
#
# `docker build` should be run from this folder

FROM ghcr.io/astral-sh/uv:python3.13-alpine

ADD . /app
WORKDIR /app

ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --compile-bytecode

# Ensure the cache folder is present and writable by anyone
# (Some command run with limited privileges)
RUN mkdir -p /.cache/uv/ && chmod 777 /.cache/uv/

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["isort"]
