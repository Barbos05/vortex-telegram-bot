# VORTEX V18 — Telegram Webhook for Render

Загрузите **bot.py, app.py, requirements.txt** и `.gitignore` в корень GitHub-репозитория.

Render → New Web Service → Python 3 → Free:

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Root Directory: пусто

Environment variables:
- `BOT_TOKEN` — токен Telegram-бота из BotFather. Никогда не публикуйте его.
- `MINI_APP_URL` — `https://vortextelegramminiapp.vercel.app/`
- `WEBHOOK_SECRET` — произвольная длинная секретная строка из букв, цифр, `_` и `-` (можно сгенерировать в Render).
- `RENDER_EXTERNAL_URL` — обычно Render устанавливает автоматически (например, `https://vortex-telegram-bot.onrender.com`). Если переменная не задана, добавьте вручную **фактический** публичный HTTPS-адрес сервиса.

После успешного Deploy зайдите на URL сервиса: `/health` должен вернуть `{"ok":true}`. Затем напишите `/start` боту.

**Ограничения бесплатного Render:** сервис может засыпать, первый ответ может задержаться. SQLite хранится на временной файловой системе; история и настройки могут пропасть после перезапуска или деплоя. Для надёжной истории потребуется внешняя база данных. Для продакшена нужна также защита от повторной обработки обновлений Telegram (идемпотентность).

**Сигналы:** направление ЛОНГ/ШОРТ выбирается случайным генератором. Статистика прибыльных сделок не ведётся; это не рыночный анализ и не инвестиционная рекомендация.
