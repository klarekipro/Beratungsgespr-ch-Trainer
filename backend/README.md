# Backend

`app/dashboard/` — функциональный локальный Python/FastAPI backend: API, SQLite repository, последовательность этапов, сценарный режим, адаптер OpenAI Responses и PDF/TXT экспорт. Запуск из корня: `python scripts/serve_dashboard.py` после установки `requirements-dashboard.txt`.

С версии 0.2 OpenAI-ход разделён на распознавание, разговорную роль клиента и отдельную проверку ответа (`customer_actor.py`). До трёх API-запросов на ход, без повторов/подмены; сохранение учебного состояния только после проверенного ответа. Поля `required` и `material` различают обязательные сведения и влияние новых сведений на решение; справочные технические детали могут иметь оба флага false.

`app/director.py`, `policy.py`, `actor.py`, `evaluation.py` и `actor_prompt.py` сохраняют исторические контракты/исследование. Новое приложение не выдаёт их прошлые результаты за приёмку нового движка.

Сервер один процесс и localhost-only. PostgreSQL и настоящие аккаунты ещё не подключены. API-key — только серверное окружение/скрытый ввод launcher. Подробности: `docs/implementation/DASHBOARD_API.md`.
