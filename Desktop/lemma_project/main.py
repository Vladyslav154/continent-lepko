import os
import uuid
import json
from fastapi import FastAPI, Request, Form, HTTPException, WebSocket, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import redis.asyncio as redis
from typing import Dict, Callable

# --- НОВАЯ, БОЛЕЕ НАДЕЖНАЯ ЛОГИКА ПЕРЕВОДА ---
def load_translations() -> Dict[str, Dict[str, str]]:
    translations = {}
    # Ищем файлы в папке 'lang'
    for lang in ['en', 'ru']:
        try:
            with open(f'lang/{lang}.json', 'r', encoding='utf-8') as f:
                translations[lang] = json.load(f)
        except FileNotFoundError:
            # Если файл не найден, логируем ошибку и используем пустой словарь
            print(f"WARNING: Translation file lang/{lang}.json not found.")
            translations[lang] = {}
    return translations

translations_data = load_translations()

def get_translator(lang: str = 'ru') -> Callable[[str], str]:
    """
    Фабрика, которая создает и возвращает функцию-переводчик для нужного языка.
    Эта функция 't' и будет передаваться в шаблон.
    """
    default_lang_data = translations_data.get('ru', {})
    lang_data = translations_data.get(lang, default_lang_data)

    def translator(key: str) -> str:
        """
        Сама функция-переводчик. Ищет ключ в словаре языка.
        Если не находит, возвращает сам ключ, а не падает с ошибкой.
        """
        return lang_data.get(key, key)

    return translator

# --- Инициализация ---
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Подключение к Redis
redis_url = os.getenv("REDIS_URL", "redis://localhost")
redis_client = redis.from_url(redis_url, decode_responses=True)


# --- Класс для управления WebSocket ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)

    async def broadcast(self, message: str, room_id: str):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_text(message)

manager = ConnectionManager()


# --- Маршруты HTTP (теперь используют новую функцию get_translator) ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, lang: str = 'ru'):
    t = get_translator(lang)
    return templates.TemplateResponse("index.html", {"request": request, "t": t, "lang": lang})

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request, lang: str = 'ru'):
    t = get_translator(lang)
    return templates.TemplateResponse("about.html", {"request": request, "t": t, "lang": lang})

@app.post("/create_pad")
async def create_pad(request: Request, lang: str = 'ru'):
    room_id = str(uuid.uuid4().hex)[:8]
    await redis_client.set(f"pad:{room_id}:exists", "1", ex=3600)
    return RedirectResponse(url=f"/pad/{room_id}?lang={lang}", status_code=303)

@app.get("/pad/{room_id}", response_class=HTMLResponse)
async def get_pad(request: Request, room_id: str, lang: str = 'ru'):
    if not await redis_client.exists(f"pad:{room_id}:exists"):
        raise HTTPException(status_code=404, detail="Комната не найдена или срок ее действия истек.")
    
    t = get_translator(lang)
    return templates.TemplateResponse("pad_room.html", {"request": request, "room_id": room_id, "t": t, "lang": lang})


# --- Маршрут WebSocket ---

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    if not await redis_client.exists(f"pad:{room_id}:exists"):
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data, room_id)
    except Exception:
        manager.disconnect(websocket, room_id)