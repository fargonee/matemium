# Reproducible Manim render environment for Matemium (ENGINE ONLY).
# 
# IMPORTANT: This uses the root context. A comprehensive .dockerignore
# ensures that website/, desktop/, server/, node_modules, target/, outputs/, media/
# etc. are NOT sent to the Docker daemon.
#
# Build: docker build -t matemium .
# Run:   docker run --rm -v "$PWD:/workspace" -w /workspace matemium render demo
#
# For the backend (Northflank etc): use server/Dockerfile with context=server/ .

FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV MATEMIUM_ROOT=/workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-science \
    dvisvgm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY pyproject.toml README.md LICENSE ./
COPY canvas ./canvas
COPY matemium ./matemium
COPY projects ./projects

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["matemium"]
CMD ["--help"]