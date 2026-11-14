#!/bin/zsh
cd -- "${0:A:h}" || exit 1
if [[ ! -x .venv/bin/python ]]; then
  print 'Start START_TRAINER.command first / Сначала запустите START_TRAINER.command.'
else
  .venv/bin/python scripts/recover_mentor.py
fi
print 'Press Enter to close / Нажмите Enter, чтобы закрыть окно.'
read -r
