# MISSION 06.1 — изолированный пилот, без применения к серверу

24.11.2026, Europe/Berlin. Подготовлен Docker-пакет для существующего Hetzner VPS. **Публикация BLOCKED:** native advisories требуют разбора; capped storage, настоящий Access/JWT path, off-host backup и AI budget ещё не приняты. Ни compose up, ни перенос данных/секретов, ни изменение действующих сервисов на VPS не выполнялись.

## Состав

- `deploy/pilot/Dockerfile`: CPython 3.14.7 Linux amd64, immutable base digest, подписанные Debian snapshot repositories от 23.11.2026, обновление base packages в этом snapshot. Python — 23 закреплённых binary wheels с hashes и `pip check`. Отдельно собрана SQLite 3.54.1 по upstream checksum; stock base содержит 3.46.1, поэтому его SQLite не используется приложением. Fonts Liberation Sans (Arial-compatible metrics) с DejaVu fallback, Poppler и ffprobe устанавливаются только в образ, не на VPS.
- `deploy/pilot/compose.yaml`: отдельный Compose project, новые собственные network/mounts, app 512 MiB/0.50 CPU, connector 128 MiB/0.10 CPU, pids/log limits, read-only root, uid/gid10001, cap_drop ALL, no-new-privileges. Оба сервиса исключены из Watchtower. Нет Docker socket, network/volume n8n/PostgreSQL, host network, privileged или published ports.
- App слушает **127.0.0.1:8100 внутри своего namespace**. Cloudflared — единственный companion в том же namespace через `network_mode: service:trainer`. Host port8100 и существующий reverse proxy не используются. Outbound network необходим для Tunnel/OpenAI; это не строгий egress allowlist. Изоляция не защищает от root/Docker administrator другого сервиса на том же host.
- `run.py`: до импорта server проверяет storage, immutable image ID/digest, source SHA и HTTPS policy; читает только отдельно предоставленный API key file, затем exec одного Uvicorn worker. `SIGTERM`, Uvicorn graceful60s и Compose75s задают окно завершения запроса. Uvicorn0.52.1 повторно поднимает SIGTERM после graceful cleanup: exit143 допустим только вместе с shutdown-complete evidence и проверенной целостностью данных, не как самостоятельный PASS.
- `asgi.py`: лимит тела6 MiB до передачи приложению; существующие ограничения документов/аудио остаются. Read-only health доступен только с loopback и возвращает минимальный SHA/SQLite/status, без конфигурации/ключей. App roles, CSRF, logout/revocation и Actor не заменялись.

## Storage — обязательный interlock

`TRAINER_DATA_PATH` в .env.example намеренно пуст. Нужен owner-created `.trainer-pilot-storage.json` с `{"project":"klareki-trainer-pilot"}` на новом выделенном mount — чужой data directory без marker не принимается. Нужен **отдельный persistent local ext4/xfs filesystem до1 GiB**, writable uid/gid10001, private permissions и минимум128 MiB free. Launcher отказывает shared root, uncapped volume, tmpfs/network FS или недостаточному запасу. Дополнительно file-size limit320 MiB ограничивает рост отдельного SQLite/WAL. Это не инструкция автоматически форматировать диск.

На VPS есть свободное место по read-only срезу, но одобренный capped mount ещё не подтверждён. Владелец выбирает отдельный ограниченный filesystem/quota arrangement; текущий launcher требует именно separate filesystem, а не обычную папку root. Provisioning/mount/fstab/форматирование здесь не выполнялись. До этого нормальный запуск обязан завершиться BLOCKED. Private audit/failure bundles и SQLite остаются внутри собственного data mount, transient files — в bounded tmpfs; никаких рабочих Mac conversations/users не переносить.

## Сборка и квалификация — только локально/в CI

Проверить чистое дерево и реальный source SHA. Пример **не является командой публикации**:

```sh
docker build --platform linux/amd64 --target runtime-deps -f deploy/pilot/Dockerfile -t trainer-deps:reviewed .
python3 tools/security/update_sbom.py --image trainer-deps:reviewed
docker build --platform linux/amd64 --target test --build-arg SOURCE_REVISION=FULL_REVIEWED_SHA -f deploy/pilot/Dockerfile -t trainer-test:reviewed .
docker run --rm --network none --read-only --cap-drop=ALL --security-opt=no-new-privileges --memory=512m --pids-limit=128 --tmpfs /tmp:size=268435456,mode=1777 trainer-test:reviewed
```

Test target использует synthetic temporary SQLite, blank/synthetic key и запрещает socket access. Локальный HTTP test contract задаётся только в test wrapper; production launcher по-прежнему требует HTTPS. Native startup/storage interlock, actual Cloudflare acceptance и AI quality не подменяются этими тестами.

Runtime собирать отдельным `--target runtime`, с тем же проверенным SHA. Записать local image ID/registry digest, source SHA, hashes Dockerfile/Python lock/SBOM, результаты CI и дату. Registry push/image transfer на VPS в этой миссии отсутствуют. Build выполняется вне VPS; нельзя отнимать CPU у действующего n8n во время сборки.

## Перед будущим запуском — действия владельца

1. Закрыть blocking findings и получить Gate PASS для фактического source SHA; проверить runtime image digest и dependency receipts. Branch protection не считается автоматически настроенной.
2. Проверить продолжительный запас VPS RAM/CPU/диска и capped mount; текущий snapshot не доказывает пиковую нагрузку. Не менять лимиты, volumes, proxy или firewall других проектов. Не применять `prune`, глобальный `down`, `down -v` или остановку Docker daemon.
3. Одобрить hostname, конкретных пользователей/retention, отдельный project-scoped OpenAI secret/model/spend stop и [Cloudflare plan](TRAINER_ACCESS_PLAN.md). Сохранённый model snapshot не заменялся; live availability и расходы не проверялись платным запросом.
4. Owner-provisioned key/credential files вне Git/.env/argv, с подходящими UID и private permissions. OpenAI key только в app secret mount, Tunnel credentials только в connector. .env содержит лишь non-secret references. Не читать/копировать существующие production keys.
5. Создать **новую** pilot SQLite и именованного mentor через существующий interactive `scripts/setup_mentor.py` в reviewed image после storage preflight. Ни default password, ни demo users автоматически не создаются; service registration публично не открывается.
6. Отдельно разрешить запуск ровно Compose project `klareki-trainer-pilot`, затем выполнить Access-denial/allow acceptance на синтетических данных и проверить SHA/readiness. В этой миссии этот шаг запрещён и не выполнялся.

## Backup/restore и rollback

`deploy/pilot/backup.py snapshot --source DB --destination NEW_BACKUP` использует SQLite backup API, а не `cp` активной WAL DB; файл/receipt private, integrity/foreign keys и content signatures сохраняются. `restore-test --source BACKUP --destination NEW_DIRECTORY` проверяет checksum и все таблицы/значения на **отдельном** восстановлении. Existing destination/live overwrite инструментом запрещён. Локальный synthetic WAL/Unicode/BLOB restore не доказывает off-host backup реального пилота.

Перед release нужны owner-approved encrypted off-host storage, retention/disk budget и отдельная проверка восстановления. Не добавлять credentials в команды/CI. Для rollback сохранять конкретный ранее квалифицированный **image ID/digest + source SHA + schema/config compatibility**, не `latest` и не mutable branch. Старой deployed pilot версии пока нет — её восстановление NOT VERIFIED.

Code rollback: остановить только собственный connector/app, проверить свежий backup, выбрать проверенный предыдущий immutable image, сохранить более новые данные, затем отдельно разрешить старт обоих. Если схема несовместима — остановиться; не накатывать старую DB молча. Data rollback требует отдельного разрешения владельца с признанием возможной потери новых бесед, safety backup и restore в новый проверяемый путь. Исходный Mac runtime, n8n/PostgreSQL и их backups не участвуют.

Источники: [FastAPI proxy trust](https://fastapi.tiangolo.com/advanced/behind-a-proxy/), [FastAPI Docker shutdown](https://fastapi.tiangolo.com/deployment/docker/), [SQLite WAL reset](https://sqlite.org/wal.html#walreset), [SQLite source manifest](https://sqlite.org/download.html), [SQLite backup](https://sqlite.org/backup.html).
