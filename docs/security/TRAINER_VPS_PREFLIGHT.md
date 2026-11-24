# VPS admission — read-only подготовка

24.11.2026. SSH к имеющемуся Hetzner VPS доступен; выполнены только uname/os-release/CPU/RAM/disk, Docker version/ps/stats/limited inspect, networks, listener и pressure metadata. Значения Env, ключи, конфигурации чужих сервисов и SQL-данные не читались. Никаких restart, install, pull/build, compose up, volume/network changes, firewall/DNS или data transfer на VPS.

Private evidence и реальные resource details хранятся вне публичного Git. Подтверждены Linux amd64, Docker/Compose, локальное filesystem, работающие n8n/PostgreSQL и другие проекты. Текущий snapshot допускает **обсуждение малого capped пилота**, но не доказывает устойчивый запас в пике. Существующий host8100 занят; новый backend его не занимает. Найдены существующие автоматические обновления: новые containers получают явный opt-out.

## Условия допуска

- Наблюдение реальной peak RAM/CPU и дискового роста; сохранить резерв для действующих проектов, не считать свободный cache гарантированным запасом. Swap usage отражает историю, а не доказанную текущую аварию.
- Собственный persistent capped filesystem до1 GiB и согласованное место под encrypted backups/staging. Обычный shared-root directory launcher отвергает. Заранее проверить UID/GID/private permissions, filesystem type, bounded logs, собственные source/image rollback refs.
- Не менять networks/volumes/ports/resources existing services. Не добавлять Docker socket/privileged/host networking. Outbound egress и shared-host trusted administrators — отдельные границы; конфигурация не выдаётся за строгую tenant isolation.
- Не строить image на VPS. Сборка/тесты — локально или standard GitHub runner; только отдельный approved image сможет позже попасть на сервер по разрешению владельца.

`deploy/pilot/preflight.sh` — воспроизводимый read-only набор команд. Результат сохранять приватно. Он не устанавливает инструменты, не делает SQL queries и не останавливает ни один контейнер. При недоступном SSH/permissions статус NOT VERIFIED, а не предположение о достаточности ресурсов.

Текущая активация **BLOCKED**: native advisory triage, capped mount, peak admission, off-host restore, реальный Access/JWT path и AI budget/model acceptance ещё не завершены. Read-only snapshot и локальная сборка не дают разрешения публикации.
