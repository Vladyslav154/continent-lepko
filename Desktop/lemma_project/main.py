import os
import uuid  # Для генерации уникальных ID
import asyncio  # Для асинхронных операций, например, в WebSocket

# Импорты для FastAPI и Starlette
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

# Импорт для работы с переменными окружения из файла .env
# Он используется ТОЛЬКО для локальной разработки.
# На Render.com переменные окружения устанавливаются напрямую через панель управления.
try:
    from dotenv import load_dotenv
    # Получаем абсолютный путь к директории, где находится main.py
    # Это гарантирует, что load_dotenv() всегда найдет файл .env,
    # если он лежит рядом с main.py.
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path=dotenv_path)
except ImportError:
    # Если python-dotenv не установлен (например, на продакшен-сервере),
    # или .env не используется, просто пропускаем загрузку из .env
    pass

# Импорты для Cloudinary
import cloudinary
import cloudinary.uploader


# --- 1. Инициализация Cloudinary ---
# Cloudinary получает ключи из переменных окружения (os.getenv)
# Эти переменные должны быть установлены в файле .env (локально)
# ИЛИ в переменных окружения на Render.com (для продакшена).
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True  # Использовать HTTPS для безопасных соединений
)


# --- 2. Начальная настройка приложения FastAPI ---
app = FastAPI(title="Lemma Tools")

# Подключаем папки для статики и шаблонов
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# --- 3. Логика для "Одноразового Файла" (Drop) - С Cloudinary ---
@app.post("/uploadfile_drop/")
async def upload_file_to_cloudinary(file: UploadFile = File(...)):
    """
    Загружает файл в Cloudinary для функции "Drop" и возвращает его публичный URL.
    """
    if not file.content_type:
        raise HTTPException(status_code=400, detail="Could not determine file type.")

    try:
        # Загрузка файла в Cloudinary
        # file.file - это объект BytesIO, который Cloudinary принимает напрямую
        # folder="drop_uploads" - опционально, для организации файлов в отдельной папке в Cloudinary
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder="drop_uploads",
            resource_type="auto", # Cloudinary сам определит, это изображение, видео или другой файл
        )

        file_url = upload_result.get("secure_url") # HTTPS URL для доступа к файлу
        public_id = upload_result.get("public_id") # Public ID для управления файлом в Cloudinary

        if not file_url:
            raise HTTPException(status_code=500, detail="Failed to get secure URL from Cloudinary.")

        # Возвращаем информацию о загруженном файле
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "cloudinary_url": file_url,
            "public_id": public_id
        }

    except Exception as e:
        # Логируем ошибку для отладки в консоли сервера
        print(f"ERROR: Cloudinary upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file to Cloudinary. Error: {e}")


# --- 4. Логика для "Общего Блокнота" (Pad) - WebSocket ---
# Примечание: app.state.board_content хранит данные в памяти и будет очищаться при
# каждом перезапуске сервера (на Render.com это происходит). Для постоянного хранения
# данных блокнота потребуется внешняя база данных.
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, board_id: str):
        await websocket.accept()
        if board_id not in self.active_connections:
            self.active_connections[board_id] = []
        self.active_connections[board_id].append(websocket)
        # Отправляем текущее содержимое доски новому подключению, если оно есть
        if board_id in app.state.board_content:
            await websocket.send_text(app.state.board_content[board_id])

    def disconnect(self, websocket: WebSocket, board_id: str):
        self.active_connections[board_id].remove(websocket)

    async def broadcast(self, message: str, board_id: str):
        # Обновляем содержимое доски в памяти
        app.state.board_content[board_id] = message
        # Отправляем новое содержимое всем активным подключениям на этой доске
        for connection in self.active_connections[board_id]:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{board_id}")
async def websocket_endpoint(websocket: WebSocket, board_id: str):
    await manager.connect(websocket, board_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data, board_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, board_id)


# --- 5. Маршруты для HTML-страниц и события запуска/остановки ---
@app.on_event("startup")
def on_startup():
    # Инициализация состояния приложения при запуске
    app.state.board_content = {} # Для хранения данных блокнота в памяти

@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/drop", response_class=HTMLResponse)
async def read_drop(request: Request):
    """
    Рендерит страницу для функции "Drop".
    ВАЖНО: JavaScript на этой странице должен отправлять файлы на /uploadfile_drop/
    """
    return templates.TemplateResponse("drop.html", {"request": request})

@app.get("/pad")
async def read_pad_random():
    """
    Перенаправляет на случайную доску блокнота.
    """
    random_id = str(uuid.uuid4())[:6] # Генерируем короткий ID для доски
    return RedirectResponse(url=f"/pad/{random_id}")

@app.get("/pad/{board_id}", response_class=HTMLResponse)
async def read_pad_with_id(request: Request, board_id: str):
    """
    Рендерит страницу блокнота для конкретного ID доски.
    """
    return templates.TemplateResponse("pad.html", {"request": request, "board_id": board_id})
    
@app.get("/qr", response_class=HTMLResponse)
async def read_qr(request: Request):
    """
    Рендерит страницу QR-генератора.
    """
    return templates.TemplateResponse("qr.html", {"request": request})