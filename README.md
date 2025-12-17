# goroskop-bot — заметки по запуску

## Тест (Windows / PowerShell)

1) Включаем venv:
```powershell
.\.venv\Scripts\Activate.ps1
```

2) Запускаем с тестовым env:
```powershell
$env:ENV_FILE=".env.test"; python app.py
```

## Прод (VPS / Linux)

1) Клоним:
```bash
git clone <repo_url>
cd goroskop-python-telegram-bot
```

2) Загружаем `.env.prod` в корень репы.

3) Запускаем деплой:
```bash
bash deploy.sh
```

4) Запуск бота:
```bash
pm2 start ecosystem.config.js
```

