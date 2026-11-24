#!/bin/sh
# READ ONLY. Run via the approved SSH connection and keep output private.
# No docker inspect Env, database queries, restart, pull, prune or compose up.
set -eu
uname -sm
cat /etc/os-release
getconf _NPROCESSORS_ONLN
uptime
free -m
df -hT /
df -i /
cat /proc/pressure/memory
docker version --format '{{.Server.Version}}'
docker compose version
docker ps --format '{{.Names}}|{{.Image}}|{{.Ports}}'
docker stats --no-stream --format '{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.PIDs}}'
docker network ls --format '{{.Name}}|{{.Driver}}'
docker system df
ss -lnt
if [ -n "${TRAINER_DATA_PATH:-}" ]; then
    findmnt -T "$TRAINER_DATA_PATH"
    df -hT "$TRAINER_DATA_PATH"
    stat -c 'uid=%u gid=%g mode=%a device=%d' "$TRAINER_DATA_PATH"
fi
