# Cloudflare Access/Tunnel — план, не созданная конфигурация

Выбран один отдельный hostname владельца для **same-origin** frontend и API. Значения hostname/team/AUD/Tunnel UUID заполняет владелец; в templates только .invalid/REPLACE placeholders. DNS, Tunnel, application/policies, certificates и секреты не создавались/не изменялись.

1. Одобрить отдельную self-hosted Access application на весь hostname/все paths. Allow только конкретным именованным пользователям/группе, подходящий IdP/MFA и ограниченный session lifetime; без public/bypass policies и без автоматического признания email header авторизацией приложения.
2. Dedicated Tunnel связывается с ровно одним loopback origin в общем namespace app/connector. Не трогать действующий Nginx, public80/443 или host8100. `compose.yaml` не публикует backend port и не присоединяется к сетям других проектов.
3. В каждой разрешённой ingress rule обязателен `originRequest.access.required: true`, точный teamName и **AUD этого application**. Cloudflared проверяет подписанный Access JWT до передачи запросов origin. Последняя rule `http_status:404`; других hostname/path маршрутов к backend быть не должно. HTTPS до edge; внутренний HTTP ограничен shared loopback namespace.
4. Сохранить фактический Host через `httpHostHeader`, один `TRAINER_ALLOWED_HOSTS`, `TRAINER_REMOTE_HTTPS=1`; Uvicorn доверяет proxy headers только127.0.0.1. Произвольный `X-Forwarded-Proto` от другого peer не превращает HTTP в HTTPS: регрессия это проверяет. Не применять trust `*` или отключение Origin/CSRF.
5. Собственная app authentication остаётся вторым слоем: Secure/HttpOnly/SameSite=strict cookies, роли, owner checks, logout/expiry/deactivation/CSRF. Access identity не даёт автоматически роль mentor и не заменяет app account. `finish` не открывает данные наставнику; нужен `submit`.
6. Не кэшировать authenticated/API/PDF/document responses в edge. Preserve no-store; не создавать cache-everything rules. На все uploads действует outer6 MiB, исходные типы/лимиты и bounded audio probing; архивные ZIP/XML bombs остаются предметом native parser security review. Native advisories нельзя скрыть Access-политикой.

## Приёмка после отдельного разрешения на новый пилот

- Разрешённый пользователь входит через Access и app; запрещённый/anonymous не получает API/static/export/body. Настоящие missing/expired/wrong-team/wrong-AUD JWT отклоняются connector, а не только edge login page.
- Прямой public IP/port, alternate hostname, старый proxy route и соседний container без shared loopback не обходят защиту. Не тестировать действующие публичные приложения других проектов.
- Проверить Host/Origin/scheme, Secure cookies, CSRF/logout, cross-user access, limits, no-store и отсутствие CORS wildcard. Не логировать auth headers, key, conversation/document bodies.
- Сверить actual source SHA/image ID, roles и private storage. До live AI теста отдельно подтвердить model availability, budget и request limits; CI работает только с mocks.

Synthetic ingress validate и unit proxy tests подтверждают конфигурационный контракт. Они **не подтверждают** действующие DNS/Access/JWT/TLS/firewall. Эти результаты сейчас NOT VERIFIED. Изоляция shared host не является защитой от root/Docker administrator другого проекта; новая app не получает таких прав.

Primary reference: [Cloudflare identity-gated edge / connector-side JWT validation](https://developers.cloudflare.com/reference-architecture/design-guides/identity-gated-edge/).
