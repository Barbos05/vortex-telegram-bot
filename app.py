"""FastAPI Telegram webhook adapter for VORTEX V18."""
import os
import logging
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
import bot

logging.basicConfig(level=logging.INFO)
SECRET = os.environ.get('WEBHOOK_SECRET', '').strip()
PUBLIC_URL = os.environ.get('RENDER_EXTERNAL_URL', '').strip().rstrip('/')

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not SECRET:
        raise RuntimeError('Set WEBHOOK_SECRET in Render environment (random secret, not bot token)')
    if not PUBLIC_URL.startswith('https://'):
        raise RuntimeError('RENDER_EXTERNAL_URL must be an HTTPS URL')
    bot.api('setWebhook', url=PUBLIC_URL+'/telegram/webhook', secret_token=SECRET,
            allowed_updates=['message','callback_query'], drop_pending_updates=False)
    bot.api('setMyCommands', commands=[
        {'command':'start','description':'Главное меню'},
        {'command':'signal','description':'Получить демо-сигнал'},
        {'command':'history','description':'История'},
        {'command':'profile','description':'Профиль'},
        {'command':'stats','description':'Статистика'},
        {'command':'risk','description':'Риск-менеджер'},
        {'command':'settings','description':'Настройки'}])
    logging.info('VORTEX webhook registered')
    yield

app = FastAPI(lifespan=lifespan)

@app.get('/')
async def home():
    return {'service':'VORTEX Telegram Bot', 'status':'running'}

@app.get('/health')
async def health():
    return {'ok':True}

@app.post('/telegram/webhook')
async def webhook(request: Request):
    provided=request.headers.get('X-Telegram-Bot-Api-Secret-Token','')
    if not secrets.compare_digest(provided, SECRET):
        raise HTTPException(status_code=403,detail='Forbidden')
    update=await request.json()
    try:
        if 'callback_query' in update:
            bot.on_callback(update['callback_query'])
        elif 'message' in update:
            bot.on_message(update['message'])
    except Exception:
        logging.exception('Telegram update processing failed')
        raise HTTPException(status_code=500,detail='Update failed')
    return {'ok':True}
