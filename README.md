# Telegram гороскоп-бот

## Поток работы бота

1. Пользователь отправляет `/start`. Бот сканирует `MEDIA_DIR` и предлагает выбрать тип гороскопа: годовой (`media/year/YYYY/sign.ext`) или месячный (`media/month/YYYY/MM/sign.ext`).
2. Для годового гороскопа: выбор года → выбор знака → создание заказа и оплата.
3. Для месячного гороскопа: выбор года → выбор месяца → выбор знака → создание заказа и оплата.
4. При выборе знака проверяется наличие файла (файлы `sign.ext` или подпапки со знаком). Создается заказ в SQLite, показывается цена и кнопка оплаты.
5. При оплате отправляется invoice через Telegram/YooKassa, после успешного платежа файл отправляется как документ. Все статусы заказа сохраняются.

## Ключевые зависимости

- `aiogram` — маршрутизация и работа с Telegram Bot API.
- `aiosqlite` — асинхронная работа с SQLite.
- `pydantic-settings` — загрузка настроек из `.env`.

Цена по умолчанию 390 ₽ (39000 копеек). База SQLite `data/bot.sqlite3`.

## Запуск

1. Создай и активируй виртуальное окружение.
2. Установи зависимости: `pip install -r requirements.txt`.
3. Заполни `.env`: `BOT_TOKEN`, `PROVIDER_TOKEN`, опционально `PRICE_KOPEKS`, `CURRENCY`, `MEDIA_DIR`, `DB_PATH`.
   - Для доступа к админ-меню (загрузка прогнозов) укажи `ADMIN_IDS` — список ID через запятую.
4. Подготовь медиа:
   - Годовой: `media/year/2025/aries.jpg`.
   - Месячный: `media/month/2025/01/aries.jpg`.
5. Запусти бота:
   ```bash
   python app.py
   ```

## Запуск с разными env

По умолчанию настройки читаются из `.env`. Для production есть шаблон `.env.prod.example`.

Варианты переключения:

- Через `APP_ENV` (берёт файл `.env.<APP_ENV>`):
  - PowerShell: ` $env:APP_ENV="prod"; python app.py `
  - PowerShell: ` $env:APP_ENV="test"; python app.py `
- Через `ENV_FILE` (явный путь к env-файлу):
  - PowerShell: ` $env:ENV_FILE=".env.prod"; python app.py `
  - PowerShell: ` $env:ENV_FILE="D:\\path\\to\\.env.custom"; python app.py `
- Через переменные окружения без файла (самый простой для CI):
  - PowerShell: ` $env:BOT_TOKEN="..."; $env:PROVIDER_TOKEN="..."; python app.py `

## Структура кода

- `app.py` — точка входа: загрузка настроек, инициализация БД, сборка бота.
- `app/config.py` — настройки, константы (месяцы, знаки, расширения).
- `app/models.py` — типы и модели (заказ).
- `app/services/` — бизнес-логика:
  - `media.py` — сканирование медиа, поиск лет/месяцев/знаков и файлов.
  - `db.py` — работа с SQLite, статусы заказов.
  - `parsing.py` — парсинг callback-данных.
  - `messaging.py` — отправка файлов.
- `app/keyboards/` — инлайн-клавиатуры для навигации и оплаты.
- `app/texts.py` — тексты и билдеры сообщений.
- `app/handlers/` — aiogram-роутеры и обработчики.

## Деплой на VPS (PM2, production)

1. Установи зависимости на сервере: `nodejs`+`npm` (если `pm2` ещё не установлен).
2. Клонируй репозиторий и зайди в папку:
   ```bash
   git clone <repo_url>
   cd goroskop-python-telegram-bot
   ```
3. Создай `.env.prod`:
   ```bash
   cp .env.prod.example .env.prod
   nano .env.prod
   ```
4. Одна команда (поставит зависимости и запустит PM2-процесс `goroskop-bot-prod`):
   ```bash
   bash prod.sh
   ```
