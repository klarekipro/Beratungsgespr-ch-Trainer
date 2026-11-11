# A35 — Release Freeze, Project Checkpoint & Demo Readiness

**Статус:** безопасный локальный checkpoint для ручной приёмки владельцем. Не финальная немецкая содержательная приёмка и не разрешение на публичный deployment. Новые функции, исправления AI, UI и зависимости в этой задаче не менялись.

Этот A35 — задание release freeze после A39 / сертификата A34 Addendum2. Прежний `A35_HANDOFF_RU.md` про компактный learner UI остаётся историческим документом.

## Точная исходная база freeze

| Параметр | Подтверждено 11.11.2026, Europe/Berlin |
|---|---|
| Папка | `/Users/admin/Documents/01_AI Business 26/17_BeratungGesprech` |
| Ветка | `codex/a39-certificate-design`, остаётся той же |
| Source/recovery HEAD до freeze-документации | `7d19a231f0833b5a920c8abc365971393653974b` |
| Запущенный code SHA | `bdc5ef9692d709e1827326647d7d240ebabaeb39` |
| Backend | `0.15.1-certificate-issuer` |
| Процесс | PID36973,127.0.0.1:8100; cwd — основная папка |
| Frontend revision | `c47616a39bda842e`;22 из22 файлов побайтно совпадают с обслуживаемыми HTTP static |
| Интерпретатор | `.venv/bin/python`, Python3.14.7; SQLite3.53.4 |
| База | `/Users/admin/Documents/01_AI Business 26/17_BeratungGesprech/runtime/dashboard/trainer.sqlite3`, WAL |
| Время read-only runtime-проверки | 11.11.2026 22:19:27 CET (UTC+01:00) |
| Согласованный data snapshot | 11.11.2026 22:22:00 CET (UTC+01:00) |

Между runtime code SHA и исходным HEAD менялись только `PROJECT_STATE.md`, `CONTINUE_FROM_HERE_RU.md`, `A39_CERTIFICATE_HANDOFF_RU.md`. Это явно зафиксированное отличие документации, не скрытая подмена backend. После freeze-коммитов Git HEAD станет ещё новее; исходники приложения и процесс остаются прежними. Точный freeze commit фиксируется при завершении ниже и в приватной квитанции checkpoint.

Tracked-файлы до начала чистые. Прежние untracked `17_BeratungGesprech_v02   /` и `Lindenhaus_A16_Import_v1/` не трогались, не включаются в release source bundle и не считаются активной установкой. Все правки этой задачи — только6 требуемых Markdown-файлов.

`git ls-remote origin` прочитан без fetch/push: удалённая `codex/a39-certificate-design` отсутствует, upstream не настроен. Remote main и локальная `origin/main` совпали: `2962a1b89cb8c9816decc8322ec92259993b3b03`. На исходном HEAD сравнение `origin/main...HEAD`:0 только в main /92 только в локальной ветке. Документационные freeze-коммиты увеличат правую величину; remote branch не появится без отдельного push. Merge/rebase/history rewrite не выполнялись. Наличие GitHub main не является резервной копией всех принятых локальных изменений.

## Резервная копия и воспроизводимость

Согласованная копия создана `sqlite3.Connection.backup()` из read-only source connection, не копированием активного WAL-файла. Поддержка подхода — [SQLite Backup API](https://www.sqlite.org/backup.html).

```text
Backup directory:
/Users/admin/Documents/01_AI Business 26/17_BeratungGesprech/runtime/release-freeze/20261111T222200+0100

Database:
/Users/admin/Documents/01_AI Business 26/17_BeratungGesprech/runtime/release-freeze/20261111T222200+0100/trainer.sqlite3
Size: 2482176 bytes
SHA-256: bc2deb68318c9b5fade7670adcd7b0086b3885320fcfc304b93f111f93ee7846
PRAGMA integrity_check (read-only backup): ok
PRAGMA foreign_key_check: 0 violations
```

Каталоги backup0700, файлы0600. В той же папке `manifest.json`: время/версия/пути, хэши и число строк всех таблиц,22 frontend-хэша, сведения о runtime/dependencies/fonts и агрегаты/идентификаторы demo и истории без текстов бесед и секретов. Приватные raw data остаются в backup, не в Git.

Дополнительно скопированы131 приватный audit/review_failure файл,1012016 bytes, с индивидуальными SHA-256 и проверкой неизменности размера/mtime при чтении. Это supplemental per-file snapshots, не обещание общей транзакции файловой системы с SQLite. Файлы `runtime/dashboard/review_failures` и `runtime/audit` важны для расследования, но печать frozen certificate PDF от них не зависит. WAL/SHM активной базы напрямую не копировались. Исходная база открывалась только read-only.

Сертификаты/снимки/сценарии/материалы и новые frozen PDF находятся внутри SQLite. Отдельные PDF на Desktop/Downloads/output не нужны для восстановления записей. Шаблоны, business materials, profiles и frontend — tracked source. Источник freeze сохраняется также в `source.bundle` в backup directory; финальный SHA/размер bundle — в `checkpoint.json` после commit, `git bundle verify` обязателен. Bundle содержит tracked историю текущей ветки, без runtime/двух чужих untracked-каталогов.

Arial regular/bold — внешняя зависимость macOS, пути/размеры/хэши сохранены в manifest. Файлы шрифтов/лицензии и Keychain не переносились на VPS. Для восстановления на этом Mac они уже установлены; для другого OS нужен отдельно проверенный Unicode font setup. Учётные записи и password hashes восстанавливаются с SQLite, OpenAI key остаётся отдельно в Keychain. Пароли/ключи/token/cookies в документы и Git не переносились.

Это локальный backup на том же Mac, не off-device disaster recovery. Фактическое восстановление в рабочую базу и отдельный полный restore drill не выполнялись. Для воспроизведения есть source bundle, pinned direct dependencies и data snapshot; побайтная переносимость macOS `.venv` на Linux не заявляется.

## Функциональная инвентаризация

«Реализовано» означает наличие пути в текущем коде. «Технически проверено» не означает качественной оценки ИИ или полной ручной приёмки. Исторические focused проверки выполнялись на отдельных временных SQLite; в этом freeze они не повторялись массово.

| Функция | Реализовано / техническое свидетельство | Ручная приёмка и что остаётся |
|---|---|---|
| Аккаунты/язык | Две роли, login/logout/password, DE/EN/RU UI, язык тренировки/диктовки отдельно; предыдущие auth/localization tests | Вход/кабинеты использовались владельцем; новый полный немецкий цикл открыт |
| Каталог случаев/AI-клиент |5 случаев и7 библиотечных профилей; доступны decisive/indecisive по назначениям. Встроенные случаи имеют DE/EN/RU training variants | Реальные DE/RU разговоры есть; ни один persona не создавался в freeze |
| AI-разговор | `simple_actor`, изоляция клиентской роли, model `gpt-4.1-mini-2025-04-14`;30 ходов/30 live-попыток на беседу | Смысловые повторы/закрытие не приняты как исправленные; полный DE-dialog завтра |
| Голос | Запись до60с/4МиБ, stop/cancel, provider transcription, ручное редактирование/отправка; session preflight | Владелец показал успешный RU/DE ввод; Safari/native permissions/другие устройства — не полная матрица |
| История/анализ | Сохранённые попытки, preliminary learner AI, три компактные вкладки/отдельные документы, PDF/TXT | Компоновка/работа с отзывом приняты владельцем; семантика AI и устойчивость обновления остаются риском |
| Отправка | Отдельная явная отправка выбранной попытки; личные попытки не открываются наставнику автоматически | Workflow проверен целевыми тестами и использовался; новая выбранная DE-попытка ещё не пройдена end-to-end |
| Mentor queue/контекст | Фильтры сотрудник/сценарий/статус, имя сотрудника отдельной колонкой; transcript/evidence/исторический snapshot, разрешённые другие попытки | Компоновка и колонка приняты; viewport/Safari/DE формулировки полностью не перепроверялись |
| Private mentor AI | Отдельная аудитория/права/exports, ручной rerun с подтверждением, сохранение предыдущего успешного результата | Есть успешные старые результаты и текущий error. Не гарантируется успешный новый анализ |
| Решение/feedback | Структурные оценки + одно поле, Save Draft, явная публикация; immutable/idempotent published result | Публикация/отзыв использовались владельцем. Исправление уже опубликованного с аудитом — backlog |
| Feedback сотрудника | Только published review, отдельное чтение текста, read receipt и статус | Размещение/чтение принято владельцем; новая DE публикация завтра |
| Сертификат | Отдельный preview/confirm, A4 PDF, recipient_full_name + issuer_full_name, stored PDF snapshot, learner ownership | Дизайн/оба редактируемых имени приняты в текущем задании. **В рабочем snapshot нет issued**, фактическая выдача пока подтверждена только изолированными тестами |
| Компания/материалы | Карточка/каталоги/условия, immutable session snapshots, MD/TXT/CSV/XLSX и text PDF import; восстановление старого контекста | Предыдущие focused checks/owner use; произвольные новые документы/сканы не гарантируются, OCR нет |
| Сценарии/персоны | Редактирование, версии/назначения/available и сохранённые снимки | Реализовано/предыдущие tests; freeze не редактировал и не повторял содержание всех случаев |
| AI configuration | Серверный Keychain/env, configured/live_enabled true, existing limits/accounting, ffprobe доступен по status | Это не проверка доступности провайдера/баланса; реальных вызовов в freeze0 |

Данные на22:22:00:33 беседы (19 finished/14 active); статусы review:23 not_submitted/3 submitted/7 reviewed.7 certificate records — все draft (2 legacy/2 a39-v1/3 a39-v2),0 issued.5 текущих analysis records:4 ready/1 error, отдельно19 analysis_history. В `published_review`1 запись нового формата; reviewed legacy нельзя автоматически считать ещё6 новыми published records.

Активны4 сотрудника и1 наставник; ещё10 неактивных записей сохраняются. Alex/`alex`:3 попытки,1 reviewed/1 submitted/1 личная;6 certificate drafts,0 issued. Полные персональные списки/тексты/пароли в report не включены.

## Эксплуатация и безопасный возврат

Проверенные точки запуска из основной папки:

```sh
cd "/Users/admin/Documents/01_AI Business 26/17_BeratungGesprech"
.venv/bin/python scripts/local_installation.py start --no-browser
.venv/bin/python scripts/local_installation.py stop
```

Также есть `START_TRAINER.command` / `STOP_TRAINER.command`. Команды приведены для оператора, **не запускались в freeze**. Launcher проверяет владельца PID/папку и не должен останавливать чужой процесс. Он получает ключ из macOS Keychain через pipe; `.env.example` не загружается автоматически. Обязательны тот же каталог данных, доступ к Keychain, существующая `.venv`/requirements и Unicode fonts; для голоса ffprobe.

**Особенность SHA:** `start` сравнивает running Git SHA с текущим HEAD и может перезапустить owned-процесс даже после документационного коммита. Сейчас приложение работает — открывать URL, не вызывать start «для проверки». Владелец завтра может явно выполнить штатный start/stop при необходимости; такая операция требует свежего backup. Ни сегодняшняя документация, ни старый README не являются поручением перезапустить сервер.

Пример согласованной новой копии перед будущим вмешательством (пишет только новый backup):

```sh
.venv/bin/python - <<'PY'
import os, sqlite3, hashlib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
os.umask(0o077)
source=Path('runtime/dashboard/trainer.sqlite3').resolve()
folder=Path('runtime/manual-backups')/datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y%m%dT%H%M%S%z')
folder.mkdir(parents=True,exist_ok=False,mode=0o700)
backup=folder/'trainer.sqlite3'
with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as src, sqlite3.connect(backup) as dst:
    src.backup(dst)
with sqlite3.connect('file:'+str(backup.resolve())+'?mode=ro',uri=True) as check:
    assert check.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
print(backup.resolve(),backup.stat().st_size,hashlib.sha256(backup.read_bytes()).hexdigest())
PY
```

Простой recovery, **только после отдельного решения владельца о возврате данных**:

1. Сначала создать новую согласованную копию текущей базы, чтобы не потерять результаты после freeze. Проверить SHA-256 сохранённого checkpoint и integrity_check read-only.
2. Остановить только свой процесс штатным stop. Сохранить текущий `runtime/dashboard` целиком отдельно, включая WAL/SHM; ничего не удалять и не смешивать старые sidecars с восстановленной базой.
3. В новом staging directory создать SQLite через backup API из выбранного checkpoint, проверить integrity/counts/снимки сертификатов. Путь/шрифты/исходники должны соответствовать версии. Не выполнять restore поверх работающего экземпляра.
4. С отдельным подтверждением заменить активный data directory подготовленной копией; сохранить оригинал и новый контрольный backup. Supplemental diagnostic/audit файлы восстанавливать как отдельный согласованный архив, не затирать более новые журналы.
5. Если потерян source checkout, сначала `git bundle verify` и восстановление Git bundle в **новую** папку; не накрывать основной каталог. Пересоздать environment из pinned requirements при необходимости; Keychain/секреты восстанавливает владелец отдельно. После явного разрешения — штатный start и read-only health/ownership/PDF checks.

`local_installation.py update/--rollback` имеет собственный snapshot/restore и может восстанавливать данные/checkout: **не использовать его как безусловную команду этого freeze**. Сегодня ни restore, ни update, ни stop/start не выполнены.

## Demo baseline

- URLs: [learner](http://127.0.0.1:8100/learner), [mentor](http://127.0.0.1:8100/mentor), очередь `/mentor#mentor/reviews`, learner history `/learner#learner/history/all`, certificates `/learner#learner/history/certificates`.
- Для короткой демонстрации выбрать существующий DE `Lindenhaus · Ein neuer Backofen für die Küche` (`lindenhaus_backofen`), Mara Weber, доступный `decisive_oven`. Это выбор по текущему каталогу/назначению, не утверждение о пройденной репетиции. Исходные RU записи остаются прежними; DE training variant формируется для новой попытки, язык UI выбирается отдельно.
- Существующий fallback-транскрипт: DE `6983e0de48e549b2b07ddb63993fad31`, finished/submitted, «Lindenhaus · Die Waschmaschine funktioniert nicht mehr». Есть и незавершённая DE `cc0ec4963c4c44e2914ff5bfdbea5ab7`; её не продолжали/не завершали в freeze. Не путать их с новой приёмочной попыткой.
- Надёжный показ сохранённых данных не требует нового AI: открыть историю/transcript/evidence и честно показать сохранённый status. Приватный AI не открывать в learner-показе; не обещать сертификат в learner-разделе при0 issued.
- Записи видео в tracked source **не найдены**. Готовый записанный demo не заявляется. Безопасный video fallback: владелец после принятого ручного цикла отдельно записывает разрешённый показ без секретов/чужих персональных данных и проверяет локальное воспроизведение. Сегодня ролик/отдельный dataset не создавались. Пока ролика нет, fallback — просмотр сохранённого разговора/документов и явно помеченного MUSTER, не симуляция нового live результата.

Риски live demo: provider/интернет/квота, schema/reference failures, повторы клиента и спорные coaching/source links, смена аккаунта в общих cookie, потеря несохранённого ввода при reload, ограничения embedded PDF/микрофона/Safari. При ошибке не зацикливать платные повторения; записать статус/время и перейти к ручной оценке/сохранённому материалу. Существующий mentor certificate listing/revoke/replace UI не обещать в сценарии: см. CERT-ADMIN-UI-001.

## Проверки и границы готовности

В freeze выполнены: Git/status/remote read-only, private health/status без логина/провайдера, cwd/PID,22 HTTP file comparisons, согласованный backup API, backup integrity/FK/hash, supplemental checksums, статическое чтение кода, `node --check` для app/learning/voice, два существующих JS-checks mentor navigation и learner compact, `git diff --check`. Они не создают беседы/публикации/сертификаты, не запускают реальный микрофон/AI и не используют рабочую базу как fixture. Предыдущие A39 focused tests имён/immutable PDF/permissions зафиксированы в A39 handoff; не выдаются за новый полноценный regression run.

Не выполнены: немецкий полный цикл, новое paid AI, реальная выдача сертификата, физическая печать, полная browser/language матрица, рабочий restore, Linux/VPS/нагрузочное/security testing. Дизайн сертификата/оба редактируемых имени считаются принятыми **по текущему поручению владельца**, не по косвенному наличию PDF.

Локальных выявленных блокеров сохранности для создания checkpoint нет: версия/исходники объяснимо согласованы, backup целостен. Финальная функциональная приёмка всё ещё открыта. Demo risks и post-demo backlog — [KNOWN_ISSUES](KNOWN_ISSUES.md), публичный пилот — [VPS assessment](A35_VPS_FEASIBILITY_RU.md).

Следующий шаг владельца: **12.11.2026 пройти [немецкий checklist](A35_GERMAN_ACCEPTANCE_CHECKLIST_RU.md)**, сохранить результат отдельно и не восстанавливать старую БД поверх новой работы. Агент не выполнил этот тест за владельца.

## Зафиксированный release checkpoint

Freeze commit: `5b2c1cdb790c131e017649cdf9e29c2ee5369303`, ветка `codex/a39-certificate-design`. Зафиксировано 2026-11-11T22:35:03.952965+01:00 (Europe/Berlin). Он содержит принятый source и6 freeze-документов; приложение в commit не менялось. Последующий документационный коммит только записывает этот полный SHA и квитанцию, не меняет baseline/source/runtime. Полный конечный branch HEAD, source bundle size/SHA-256 и результаты сохранности данных находятся в `checkpoint.json` указанной backup directory. Running code остаётся `bdc5ef9692d709e1827326647d7d240ebabaeb39` /PID36973, без restart.
