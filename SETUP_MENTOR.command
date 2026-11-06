#!/bin/zsh
cd -- "${0:A:h}" || exit 1
if [[ ! -x .venv/bin/python ]]; then
  print 'Сначала запустите START_TRAINER.command.'
else
  .venv/bin/python scripts/setup_mentor.py
fi
print 'Нажмите Enter, чтобы закрыть окно.'
read -r
