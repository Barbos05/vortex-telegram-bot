"""VORTEX V18 Telegram bot. Python 3.10+, stdlib only, long polling."""
import json, os, sqlite3, time, urllib.request, urllib.parse, urllib.error, logging, datetime, secrets
from pathlib import Path

TOKEN=os.environ.get('BOT_TOKEN','').strip()
APP_URL=os.environ.get('MINI_APP_URL','https://vortextelegramminiapp.vercel.app/').strip()
DB=os.environ.get('DB_PATH',str(Path(__file__).with_name('vortex.db')))
if not TOKEN: raise SystemExit('Set BOT_TOKEN environment variable; never commit the token.')
BASE=f'https://api.telegram.org/bot{TOKEN}/'
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
con=sqlite3.connect(DB,timeout=15,isolation_level=None)
con.execute('PRAGMA journal_mode=WAL')
con.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, first_name TEXT, joined TEXT NOT NULL, notifications INTEGER NOT NULL DEFAULT 0, awaiting TEXT NOT NULL DEFAULT "")')
con.execute('CREATE TABLE IF NOT EXISTS signals(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, asset TEXT NOT NULL, direction TEXT NOT NULL, created TEXT NOT NULL)')
ASSETS=['EUR/USD','XAUUSD','GBP/USD','NAS100','USD/JPY','BTCUSDT']

def api(method, **data):
    payload=json.dumps(data,ensure_ascii=False).encode()
    req=urllib.request.Request(BASE+method,data=payload,headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=45) as r: response=json.load(r)
    if not response.get('ok'): raise RuntimeError(response.get('description','Telegram API error'))
    return response.get('result')

def kb(rows): return {'inline_keyboard':rows}
def btn(label,action):return {'text':label,'callback_data':action}
def menu():
    return kb([[{'text':'🚀 Открыть терминал','web_app':{'url':APP_URL}}],
               [btn('📊 Получить сигнал','choose'),btn('📜 История','history')],
               [btn('👤 Профиль','profile'),btn('📈 Статистика','stats')],
               [btn('🛡 Риск-менеджер','risk'),btn('⚙️ Настройки','settings')]])
def send(chat,text,markup=None):
    args={'chat_id':chat,'text':text,'parse_mode':'HTML'}
    if markup:args['reply_markup']=markup
    return api('sendMessage',**args)
def edit(chat,msg,text,markup=None):
    args={'chat_id':chat,'message_id':msg,'text':text,'parse_mode':'HTML'}
    if markup:args['reply_markup']=markup
    try:return api('editMessageText',**args)
    except Exception:return send(chat,text,markup)
def now():return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
def ensure(user):
    uid=user['id'];name=user.get('first_name','Трейдер')
    con.execute('INSERT OR IGNORE INTO users(id,first_name,joined) VALUES(?,?,?)',(uid,name,now()))
    con.execute('UPDATE users SET first_name=? WHERE id=?',(name,uid))
def back():return kb([[btn('← Главное меню','menu')]])
def signal_menu():
    return kb([[btn(x,'asset:'+x) for x in ASSETS[i:i+2]] for i in range(0,len(ASSETS),2)]+[[btn('← Главное меню','menu')]])
def screen(uid,action):
    if action=='menu':return ('⚡ <b>VORTEX</b> — торговый терминал\n\nВыбери нужный раздел:',menu())
    if action=='choose':return ('📊 <b>Выбери актив</b>\n\nНаправление ЛОНГ/ШОРТ — тестирование стратегии Smart Money.',signal_menu())
    if action.startswith('asset:'):
        asset=action[6:]
        if asset not in ASSETS:return ('Неизвестный актив.',signal_menu())
        direction='ЛОНГ 🟢' if secrets.randbelow(2)==0 else 'ШОРТ 🔴'
        con.execute('INSERT INTO signals(user_id,asset,direction,created) VALUES(?,?,?,?)',(uid,asset,direction,now()))
        return (f'⚡ <b>VORTEX / DEMO</b>\n\nАктив: <b>{asset}</b>\nНаправление: <b>{direction}</b>\n\ВАШ СИГНАЛ ГОТОВ ✅',kb([[btn('🔄 Ещё сигнал','choose')],[btn('📜 История','history'),btn('🏠 Меню','menu')]]))
    if action=='history':
        rows=con.execute('SELECT asset,direction,created FROM signals WHERE user_id=? ORDER BY id DESC LIMIT 10',(uid,)).fetchall()
        body='\n'.join(f'• {a} — {d} · {t}' for a,d,t in rows) if rows else 'Сигналов пока нет.'
        return ('📜 <b>Последние 10 сигналов</b>\n\n'+body+'\n\nЭто история выданных направлений, не закрытых сделок.',back())
    if action=='profile':
        name,joined=con.execute('SELECT first_name,joined FROM users WHERE id=?',(uid,)).fetchone()
        count=con.execute('SELECT COUNT(*) FROM signals WHERE user_id=?',(uid,)).fetchone()[0]
        return (f'👤 <b>Личный кабинет</b>\n\nИмя: {esc(name)}\nTelegram ID: <code>{uid}</code>\nРегистрация: {joined}\nВыдано направлений: <b>{count}</b>',back())
    if action=='stats':
        count=con.execute('SELECT COUNT(*) FROM signals WHERE user_id=?',(uid,)).fetchone()[0]
        long_count=con.execute("SELECT COUNT(*) FROM signals WHERE user_id=? AND direction LIKE 'ЛОНГ%'",(uid,)).fetchone()[0]
        return (f'📈 <b>Статистика</b>\n\nВсего направлений: {count}\nЛОНГ: {long_count}\nШОРТ: {count-long_count}\n\nВинрейт недоступен: результаты закрытых сделок не отслеживаются. 85% на сайте — демонстрационная цифра.',back())
    if action=='settings':
        state=con.execute('SELECT notifications FROM users WHERE id=?',(uid,)).fetchone()[0]
        return (f'⚙️ <b>Настройки</b>\n\nУведомления: {"включены" if state else "выключены"}\n\nПока это настройка предпочтения. Автоматическая рассылка реальных рыночных сигналов не подключена.',kb([[btn('🔔 Переключить уведомления','toggle')],[btn('← Главное меню','menu')]]))
    if action=='toggle':
        con.execute('UPDATE users SET notifications=1-notifications WHERE id=?',(uid,))
        return screen(uid,'settings')
    if action=='risk':
        con.execute("UPDATE users SET awaiting='risk' WHERE id=?",(uid,))
        return ('🛡 <b>Риск-менеджер</b>\n\nОтправь сообщение в формате:\n<code>1000 1</code>\n\nПервое число — депозит в USD, второе — риск в процентах. Например, 1000 USD и 1% = 10 USD допустимого убытка.\n\nЭто расчёт риска, не прогноз дохода.',back())
    return screen(uid,'menu')
def esc(s):return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def on_message(msg):
    user=msg.get('from',{});uid=user.get('id');chat=msg['chat']['id'];text=msg.get('text','').strip()
    if not uid:return
    ensure(user)
    if text.startswith('/start') or text.startswith('/menu'):
        con.execute("UPDATE users SET awaiting='' WHERE id=?",(uid,))
        body,markup=screen(uid,'menu');send(chat,body,markup);return
    if text.startswith('/help'):
        send(chat,'Команды: /start, /menu, /signal, /history, /profile, /stats, /risk, /settings');return
    commands={'/signal':'choose','/history':'history','/profile':'profile','/stats':'stats','/risk':'risk','/settings':'settings'}
    command=text.split()[0].split('@')[0] if text else ''
    if command in commands:
        body,markup=screen(uid,commands[command]);send(chat,body,markup);return
    awaiting=con.execute('SELECT awaiting FROM users WHERE id=?',(uid,)).fetchone()[0]
    if awaiting=='risk':
        try:
            parts=text.replace(',','.').split()
            if len(parts)!=2:raise ValueError()
            deposit,pct=map(float,parts)
            if not (0<deposit<=1e9 and 0<pct<=100):raise ValueError()
            con.execute("UPDATE users SET awaiting='' WHERE id=?",(uid,))
            send(chat,f'🛡 <b>Расчёт риска</b>\n\nДепозит: ${deposit:,.2f}\nРиск: {pct:g}%\nМаксимальный плановый убыток: <b>${deposit*pct/100:,.2f}</b>\n\nФактический убыток может превысить плановый из-за проскальзывания.',back())
        except ValueError:send(chat,'Укажи два числа, например: <code>1000 1</code>',back())
        return
    body,markup=screen(uid,'menu');send(chat,body,markup)
def on_callback(cb):
    user=cb.get('from',{});uid=user.get('id');msg=cb.get('message',{});chat=msg.get('chat',{}).get('id');mid=msg.get('message_id')
    if not uid or not chat:return
    ensure(user)
    api('answerCallbackQuery',callback_query_id=cb['id'])
    action=cb.get('data','menu')
    if action!='risk':con.execute("UPDATE users SET awaiting='' WHERE id=?",(uid,))
    body,markup=screen(uid,action)
    if action=='risk':send(chat,body,markup)
    else:edit(chat,mid,body,markup)
def main():
    api('deleteWebhook',drop_pending_updates=False)
    api('setMyCommands',commands=[{'command':'start','description':'Главное меню'},{'command':'signal','description':'Получить демо-сигнал'},{'command':'history','description':'История сигналов'},{'command':'profile','description':'Мой профиль'},{'command':'stats','description':'Статистика'},{'command':'risk','description':'Риск-менеджер'},{'command':'settings','description':'Настройки'}])
    logging.info('VORTEX bot started')
    offset=None
    while True:
        try:
            updates=api('getUpdates',offset=offset,timeout=30,allowed_updates=['message','callback_query'])
            for update in updates:
                offset=update['update_id']+1
                try:
                    if 'callback_query' in update:on_callback(update['callback_query'])
                    elif 'message' in update:on_message(update['message'])
                except Exception:logging.exception('Failed update %s',update.get('update_id'))
        except (urllib.error.URLError,TimeoutError,RuntimeError) as ex:
            logging.warning('Polling error: %s',ex);time.sleep(4)
if __name__=='__main__':main()
