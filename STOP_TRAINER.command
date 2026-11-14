#!/bin/zsh
# Finder/LaunchServices entry point; cwd never determines the installed project.
TRAINER_ROOT="$(cd -- "$(dirname -- "$0")" && pwd -P)" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
TRAINER_PYTHON="$TRAINER_ROOT/.venv/bin/python"
if [[ ! -x "$TRAINER_PYTHON" ]]; then
  TRAINER_PYTHON="$(command -v python3)"
fi
if [[ -z "$TRAINER_PYTHON" ]] || ! "$TRAINER_PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3,10))'; then
  print 'Нужен Python 3.10 или новее. Установите Python и повторите запуск.'
  read '?Нажмите Enter…'
  exit 1
fi
"$TRAINER_PYTHON" "$TRAINER_ROOT/scripts/local_installation.py" stop "$@"
TRAINER_EXIT=$?
if (( TRAINER_EXIT != 0 )); then
  read '?Нажмите Enter, чтобы закрыть это окно…'
fi
exit "$TRAINER_EXIT"
