FROM python:3.14.7-slim-trixie@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d AS base
# Frozen Debian repositories: repeat builds do not silently resolve a different OS graph.
RUN rm /etc/apt/sources.list.d/debian.sources && printf '%s\n' \
    'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20261123T000000Z trixie main' \
    'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian-security/20261123T000000Z trixie-security main' \
    > /etc/apt/sources.list && apt-get update && apt-get upgrade -y --no-install-recommends && apt-get install -y --no-install-recommends \
    ca-certificates ffmpeg poppler-utils fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

FROM base AS sqlite-build
RUN apt-get update && apt-get install -y --no-install-recommends gcc make libc6-dev && rm -rf /var/lib/apt/lists/*
# SHA256 computed only after matching the official SHA3-256 download manifest.
ADD --checksum=sha256:926ef8d3eab93fbf6e06011901273eec076b25594a4e1cdadd50c987f4f6d64e https://sqlite.org/2026/sqlite-autoconf-3540100.tar.gz /tmp/sqlite.tar.gz
RUN mkdir /tmp/sqlite && tar -xzf /tmp/sqlite.tar.gz -C /tmp/sqlite --strip-components=1 && \
    cd /tmp/sqlite && CFLAGS='-O1 -g0' ./configure --prefix=/opt/sqlite --enable-shared --disable-static && \
    make -j2 libsqlite3.so && mkdir -p /opt/sqlite/lib && cp libsqlite3.so /opt/sqlite/lib/libsqlite3.so.0 && \
    ln -s libsqlite3.so.0 /opt/sqlite/lib/libsqlite3.so

FROM base AS runtime-deps
COPY --from=sqlite-build /opt/sqlite/lib/libsqlite3.so* /usr/local/lib/
RUN ldconfig && python -c 'import sqlite3; assert sqlite3.sqlite_version == "3.54.1"'
COPY deploy/pilot/requirements-linux-amd64.txt /tmp/requirements.txt
RUN python -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: --require-hashes --no-deps \
    -r /tmp/requirements.txt && python -m pip check && \
    mkdir -p /usr/share/trainer-build && dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\n' > /usr/share/trainer-build/os-packages.tsv


RUN apt-get update && apt-get install -y --no-install-recommends fonts-liberation2 && rm -rf /var/lib/apt/lists/* && \
    dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\n' > /usr/share/trainer-build/os-packages.tsv

# Build-input attestation prevents accidentally generating a new SBOM from an old local tag.
COPY requirements-dashboard.txt /usr/share/trainer-build/inputs/requirements-dashboard.txt
COPY deploy/pilot/Dockerfile deploy/pilot/requirements-linux-amd64.txt deploy/pilot/python-lock.json /usr/share/trainer-build/inputs/deploy/pilot/
RUN python -c 'from pathlib import Path; import json,hashlib; r=Path("/usr/share/trainer-build/inputs"); names=["requirements-dashboard.txt","deploy/pilot/Dockerfile","deploy/pilot/requirements-linux-amd64.txt","deploy/pilot/python-lock.json"]; Path("/usr/share/trainer-build/input-sha256.json").write_text(json.dumps({n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in names}))'

FROM runtime-deps AS runtime
ARG SOURCE_REVISION
LABEL org.opencontainers.image.source="https://github.com/klarekipro/Beratungsgespr-ch-Trainer" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/opt/trainer \
    TRAINER_DATA_DIR=/var/lib/trainer/dashboard TRAINER_AUDIT_DIR="" TRAINER_REMOTE_HTTPS=1 \
    TRAINER_FONT_PATH=/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf \
    TRAINER_BOLD_FONT_PATH=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf
WORKDIR /opt/trainer
COPY backend/ backend/
COPY frontend/ frontend/
COPY profiles/ profiles/
COPY materials/ materials/
COPY scripts/setup_mentor.py scripts/setup_mentor.py
COPY deploy/pilot/ deploy/pilot/
RUN printf '{"source_revision":"%s"}\n' "$SOURCE_REVISION" > BUILD_INFO.json && \
    mkdir -p /var/lib/trainer && chown 10001:10001 /var/lib/trainer && chmod 700 /var/lib/trainer
USER 10001:10001
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=4s --start-period=30s --retries=3 CMD ["python", "deploy/pilot/healthcheck.py"]
CMD ["python", "deploy/pilot/run.py"]

FROM runtime AS test
COPY tests/ tests/
COPY tools/security/ tools/security/
CMD ["python", "tools/security/offline_tests.py", "--output", "/tmp/trainer-tests.json"]
