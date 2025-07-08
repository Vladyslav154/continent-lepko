# Проект Lepko - Полные инструкции по запуску

## Описание
Lepko - это веб-приложение на FastAPI с поддержкой многоязычности и Redis для кэширования.

## Системные требования
- Python 3.9 или выше
- Redis сервер
- Git (опционально)

## Установка зависимостей

### 1. Установка Python
**Windows:**
- Скачайте Python с https://python.org/downloads/
- При установке отметьте "Add Python to PATH"

**macOS:**
```bash
# Через Homebrew
brew install python3
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### 2. Установка Redis

**Windows:**
- Скачайте Redis для Windows с GitHub: microsoft/redis
- Или используйте WSL2 с Ubuntu

**macOS:**
```bash
brew install redis
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
```

## Запуск проекта

### 1. Распакуйте архив
```bash
unzip lepko.zip
cd lepko
```

### 2. Создайте виртуальное окружение
```bash
python -m venv venv

# Активация на Linux/macOS:
source venv/bin/activate

# Активация на Windows:
venv\Scripts\activate
```

### 3. Установите зависимости Python
```bash
pip install -r requirements.txt
```

### 4. Запустите Redis сервер

**Linux/macOS:**
```bash
redis-server
```

**Windows:**
```bash
redis-server.exe
```

**Альтернативно (если Redis установлен как сервис):**
```bash
# Linux
sudo systemctl start redis

# macOS
brew services start redis

# Windows
net start redis
```

### 5. Запустите FastAPI приложение
```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

## Тестирование

### 1. Откройте браузер и перейдите по адресам:
- Главная страница: http://localhost:8001
- API документация: http://localhost:8001/docs
- Альтернативная документация: http://localhost:8001/redoc

### 2. Проверьте основные функции:
- Смена языка (русский/английский)
- Работа форм
- API эндпоинты через /docs

### 3. Тестирование API через curl:
```bash
# Получить переводы
curl http://localhost:8001/api/translations

# Проверить статус
curl http://localhost:8001/api/status
```

## Структура проекта
```
lepko/
├── main.py              # Основное FastAPI приложение
├── translations.py      # Система переводов
├── requirements.txt     # Python зависимости
├── templates/          # HTML шаблоны
│   ├── index.html
│   └── ...
├── static/            # Статические файлы
│   ├── css/
│   ├── js/
│   └── images/
└── README.md          # Этот файл
```

## Решение проблем

### Проблема: "Port 8001 is already in use"
```bash
# Найти процесс использующий порт
lsof -i :8001  # Linux/macOS
netstat -ano | findstr :8001  # Windows

# Убить процесс или использовать другой порт
uvicorn main:app --host 0.0.0.0 --port 8002
```

### Проблема: "redis.exceptions.ConnectionError"
- Убедитесь что Redis сервер запущен
- Проверьте что Redis слушает на порту 6379:
```bash
redis-cli ping
# Должен ответить: PONG
```

### Проблема: "ModuleNotFoundError"
- Убедитесь что виртуальное окружение активировано
- Переустановите зависимости:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Проблема: Виртуальное окружение не активируется
**Windows PowerShell:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1
```

**Windows Command Prompt:**
```cmd
venv\Scripts\activate.bat
```

## Остановка приложения
- Нажмите Ctrl+C в терминале где запущен uvicorn
- Остановите Redis сервер:
```bash
# Если запущен вручную - Ctrl+C
# Если как сервис:
sudo systemctl stop redis  # Linux
brew services stop redis   # macOS
net stop redis            # Windows
```

## Дополнительные команды

### Просмотр логов Redis:
```bash
redis-cli monitor
```

### Очистка кэша Redis:
```bash
redis-cli flushall
```

### Проверка статуса приложения:
```bash
curl http://localhost:8001/health
```

## Поддержка
При возникновении проблем проверьте:
1. Версию Python: `python --version`
2. Статус Redis: `redis-cli ping`
3. Установленные пакеты: `pip list`
4. Логи приложения в терминале

Приложение должно быть доступно по адресу: http://localhost:8001
