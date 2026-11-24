"""Dedicated pilot entrypoint. Does not alter the existing macOS launcher."""
import json
import os
from pathlib import Path
import resource
import sys

ROOT = Path(__file__).resolve().parents[2]


def storage_preflight(path):
    path = Path(path)
    if not path.is_dir() or path.is_symlink() or not os.access(path, os.W_OK):
        raise RuntimeError('Pilot storage must already exist, be writable and be reviewed by the owner')
    marker = path/'.trainer-pilot-storage.json'
    if marker.is_symlink() or not marker.is_file() or json.loads(marker.read_text()).get('project') != 'klareki-trainer-pilot':
        raise RuntimeError('Owner-provisioned pilot storage marker missing; refusing an unrelated data directory')
    info = os.statvfs(path)
    total, free = info.f_blocks*info.f_frsize, info.f_bavail*info.f_frsize
    if total > 1024**3 or free < 128*1024**2 or os.stat(path).st_dev == os.stat('/').st_dev:
        raise RuntimeError('Pilot requires a separate capped local filesystem <=1 GiB and >=128 MiB free; shared root is forbidden')
    # Reject ephemeral/network backing stores. A separate mounted ext4/xfs filesystem is required.
    entries = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        left, right = line.split(' - ', 1)
        mount = left.split()[4].replace('\\040', ' ')
        if str(path) == mount or str(path).startswith(mount.rstrip('/')+'/'):
            entries.append((len(mount), right.split()[0]))
    if not entries or max(entries)[1] not in ('ext4', 'xfs'):
        raise RuntimeError('Persistent local ext4/xfs storage was not verified')


def main():
    os.umask(0o077)
    storage_preflight(Path(os.environ['TRAINER_DATA_DIR']).parent)
    import re
    image = os.environ.get('TRAINER_IMAGE_REF','')
    if not re.fullmatch(r'(?:sha256:[0-9a-f]{64}|[A-Za-z0-9._/:-]+@sha256:[0-9a-f]{64})', image):
        raise RuntimeError('Use an owner-reviewed immutable image ID or registry digest')
    if os.environ.get('TRAINER_REMOTE_HTTPS') != '1':
        raise RuntimeError('Remote HTTPS enforcement must remain enabled')
    host = os.environ.get('TRAINER_ALLOWED_HOSTS', '')
    if not host or any(c in host for c in ('*', ',', '/', ':', ' ')):
        raise RuntimeError('One exact pilot hostname must be approved')
    build = json.loads((ROOT/'BUILD_INFO.json').read_text())
    import re
    if not re.fullmatch(r'[0-9a-f]{40}', build.get('source_revision', '')):
        raise RuntimeError('An immutable source SHA is required')
    secret = os.environ.get('OPENAI_API_KEY_FILE')
    if secret:
        p = Path(secret)
        if p.is_symlink() or p.stat().st_mode & 0o037:
            raise RuntimeError('Unsafe API key file permissions')
        os.environ['OPENAI_API_KEY'] = p.read_text().strip()
    # Bound each file as well as the filesystem; prevents a growing WAL consuming the host.
    resource.setrlimit(resource.RLIMIT_FSIZE, (320*1024**2, 320*1024**2))
    os.chdir(ROOT)
    os.execv(sys.executable, [sys.executable, '-m', 'uvicorn', 'deploy.pilot.asgi:create_app', '--factory',
             '--host', '127.0.0.1', '--port', '8100', '--workers', '1', '--proxy-headers',
             '--forwarded-allow-ips', '127.0.0.1', '--limit-concurrency', '8',
             '--timeout-graceful-shutdown', '60', '--no-access-log'])


if __name__ == '__main__':
    main()
