import os
import json
import secrets
import redis
import bleach
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from coinbase_commerce.client import Client

# --- 1. Настройки и константы ---
app = FastAPI(title="Continent Lepko")

# Переменные окружения
SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-for-local-dev')
COINBASE_API_KEY = os.getenv('COINBASE_API_KEY', 'DEFAULT_KEY')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Настройки Drop
UPLOAD_FOLDER = 'temp_uploads'
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar'}

# --- 2. Инициализация ---
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
coinbase_client = Client(api_key=COINBASE_API_KEY)

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
except redis.exceptions.ConnectionError as e:
    print(f"COULD NOT CONNECT TO REDIS: {e}")
    redis_client = None


# --- 3. Логика перевода ---
TRANSLATIONS = {}
LANGUAGES = {'en': 'EN', 'ru': 'RU', 'de': 'DE', 'cs': 'CS', 'uk': 'UK'}

def load_translations():
    lang_dir = os.path.join('static', 'lang')
    for lang_code in LANGUAGES:
        file_path = os.path.join(lang_dir, f'{lang_code}.json')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                TRANSLATIONS[lang_code] = json.load(f)

load_translations()

# --- 4. Главная функция для рендеринга шаблонов ---
def render(template_name: str, request: Request, context: dict = {}):
    lang_code = request.query_params.get('lang', request.session.get('lang', 'en'))
    if lang_code not in LANGUAGES:
        lang_code = 'en'
    request.session['lang'] = lang_code

    def t(key: str, **kwargs):
        text = TRANSLATIONS.get(lang_code, {}).get(key, key)
        return text.format(**kwargs) if kwargs else text

    # Добавляем данные счетчиков в контекст каждой страницы
    if redis_client:
        files_count = redis_client.get('counter:files') or 0
        links_count = redis_client.get('counter:links') or 0
        context['counters'] = {'files': int(files_count), 'links': int(links_count)}
    else:
        context['counters'] = {'files': 0, 'links': 0}

    full_context = {"request": request, "t": t, "LANGUAGES": LANGUAGES, "current_lang": lang_code, **context}
    return templates.TemplateResponse(template_name, full_context)

# --- 5. Маршруты ---

@app.get("/", response_class=HTMLResponse)
async def route_root(request: Request):
    return render("home.html", request)

# --- Drop с валидацией ---
@app.get("/drop", response_class=HTMLResponse)
async def route_get_drop(request: Request):
    return render("drop.html", request, {"error": None})

@app.post("/drop", response_class=HTMLResponse)
async def route_post_drop(request: Request, file: UploadFile = File(...)):
    t = render("", request).context['t']
    file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if file_ext not in ALLOWED_EXTENSIONS:
        error = t('drop_error_file_type', allowed_types=", ".join(ALLOWED_EXTENSIONS))
        return render("drop.html", request, {"error": error})
    
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        error = t('drop_error_file_size', max_size=f"{MAX_FILE_SIZE / 1024 / 1024:.1f} MB")
        return render("drop.html", request, {"error": error})
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    with open(file_path, "wb") as buffer:
        buffer.write(data)
    
    if redis_client:
        redis_client.incr('counter:files')
        redis_client.incr('counter:links')

    download_link = str(request.base_url) + 'uploads/' + filename
    return HTMLResponse(f'<h1>{t("drop_success_title")}</h1><p>{t("drop_success_message")} <a href="{download_link}">{download_link}</a></p><a href="/drop">{t("drop_success_back_button")}</a>')

@app.get("/uploads/{filename}")
async def route_get_upload(filename: str):
    return FileResponse(path=os.path.join(UPLOAD_FOLDER, filename), filename=filename)

# --- Pad с паролями и Redis ---
@app.get("/pad", response_class=HTMLResponse)
async def route_get_pad(request: Request):
    return render("pad.html", request)

@app.post("/pad/create")
async def route_create_pad_room(request: Request, password: str = Form(...)):
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis connection not available")
    room_id = secrets.token_urlsafe(6)
    hashed_password = generate_password_hash(password)
    redis_client.setex(f"pad:password:{room_id}", 3600, hashed_password)
    redis_client.incr('counter:links')
    return RedirectResponse(url=f"/pad/{room_id}", status_code=303)

@app.get("/pad/{room_id}", response_class=HTMLResponse)
async def route_get_pad_room(request: Request, room_id: str):
    if not redis_client or not redis_client.exists(f"pad:password:{room_id}"):
        raise HTTPException(status_code=404, detail="Room not found or expired")
    return render("pad_room.html", request, {"room_id": room_id})

@app.post("/pad/{room_id}/enter")
async def route_enter_pad_room(request: Request, room_id: str, password: str = Form(...)):
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis connection not available")
    
    stored_hash = redis_client.get(f"pad:password:{room_id}")
    if stored_hash and check_password_hash(stored_hash, password):
        # Пароль верный, показываем редактор
        return render("pad_editor.html", request, {"room_id": room_id})
    # Пароль неверный, показываем ошибку
    return render("pad_room.html", request, {"room_id": room_id, "error": True})

# --- Upgrade и Coinbase ---
@app.get("/upgrade", response_class=HTMLResponse)
async def route_get_upgrade(request: Request):
    return render("upgrade.html", request)

@app.post("/create_charge")
async def route_create_charge(request: Request):
    t = render("", request).context['t']
    charge = coinbase_client.charge.create(
        name=t('premium_charge_name'),
        description=t('premium_charge_description'),
        local_price={'amount': '10.00', 'currency': 'USD'},
        pricing_type='fixed_price',
        redirect_url=str(request.base_url) + 'payment_success',
        cancel_url=str(request.base_url) + 'upgrade'
    )
    if redis_client:
        redis_client.incr('counter:links')
    return RedirectResponse(charge.hosted_url, status_code=303)

@app.get("/payment_success")
async def route_payment_success(request: Request):
    t = render("", request).context['t']
    return HTMLResponse(f"<h1>{t('payment_success_title')}</h1><p>{t('payment_success_message')}</p>")