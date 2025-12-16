# Agent guide

Краткие ориентиры по проекту для быстрых правок.

## Быстрый старт
- Точка входа: `app.py` (`python app.py`), создает бота, грузит настройки из `.env`, инициализирует SQLite.
- Важные env: `BOT_TOKEN`, `PROVIDER_TOKEN`, `PRICE_KOPEKS`, `MEDIA_DIR`, `DB_PATH`, `ADMIN_IDS`.
- Библиотеки: `aiogram 3.x`, `aiosqlite`, `pydantic-settings`.

## Карта модулей
- `app/features/user/handlers.py` — пользовательская навигация, оплата, доставка файла, запрос отзыва.
- `app/features/admin/handlers.py` — админ-меню: добавление/удаление контента, статистика, просмотр отзывов.
- `app/features/user/keyboards.py` — инлайн-клавиатуры навигации/оплаты/отзывов.
- `app/features/admin/keyboards.py` — инлайн-клавиатуры админки.
- `app/texts.py` — все текстовые ответы.
- `app/services/db.py` — SQLite: таблицы `orders`, `reviews`, CRUD/статистика/отзывы.
- `app/services/media.py` — проверка/поиск медиаконтента (гороскопы, бонусы за отзывы).
- `app/services/messaging.py` — отправка файлов через Telegram.
- `app/services/parsing.py` — парсинг callback/payload для продуктов/навигации.
- `app/config.py` — pydantic-настройки и словари (знаки, месяцы).
- `app/models.py` — TypedDict для `Order` и `Review`.

## Основные потоки
- **Навигация контента**: `user/handlers.py` обрабатывает выбор года/месяца/знака, проверяет наличие файлов через `media.py`, строит клавиатуры.
- **Оплата**: callback `pay:*` → `send_invoice`; pre-checkout валидирует payload и наличие контента; при `successful_payment` создается оплаченный заказ (`create_paid_order`), шлется сообщение об успехе, затем файл.
- **Доставка файла**: `deliver_file` → `messaging.send_content` (FSInputFile с меткой mtime) + `db.mark_delivered`.
- **Отзывы**: после успешной доставки шлется клавиатура с отзывом/пропуском. `reviews` таблица хранит `submitted/declined`. Текстовое сообщение пользователя сохраняет отзыв, пропуск фиксируется отдельно.
- **Бонус за отзыв**: если в `media/reviews/<sign>/<sign>.(jpg|png|webp)` есть файл, после отправки текста отзыва бот шлет эту картинку с подписью.
- **Админка**: проверка по `ADMIN_IDS`. Статистика продаж (`fetch_sales_stats`) и просмотр последних отзывов (`fetch_recent_reviews`) с датой/пользователем/продуктом.
- **Админка → изображения после отзывов**: кнопка «Добавить изображения после отзывов» позволяет загрузить файл на знак; сохраняется в `media/reviews/<sign>/`.

## Медиа
- Структура: `media/year/<YYYY>/<sign>.<ext>` и `media/month/<YYYY>/<MM>/<sign>.<ext>`.
- Допустимые расширения: `jpg`, `jpeg`, `png`, `webp`.
