# Брендинг текущего A17

Отдельного файла логотипа в frontend нет. Используется HTML/CSS: знак `K·`, текст `klare ki` и локализованный подзаголовок. Оригинальная разметка из `frontend/app.js` приведена ниже; все используемые стили `.brand`, `.brand-mark`, `.brand-text`, `.brand-sub` сохранены без изменений в `sources/frontend/styles.css` и `portals.css`. Новый логотип для пакета не создавался.

```html
<a class="brand" href="#${role}/${mentor?"overview":"practice"}" aria-label="Klare KI — ${window.TrainerI18n.t("dashboard.text_036")}"><span class="brand-mark" aria-hidden="true">K<span>·</span></span><div><div class="brand-text">klare ki</div><div class="brand-sub">${window.TrainerI18n.t("dashboard.text_037")}</div></div></a>
```

`assets/logo-mark.html` — отдельное представление существующего знака и немецкой подписи, извлечённых из исходной разметки; подключает неизменённые CSS. Это не новый оригинальный файл логотипа. Брендинг в контексте приложения виден на всех кадрах.
