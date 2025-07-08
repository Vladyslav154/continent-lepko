
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv # Убедитесь, что python-dotenv установлен: pip install python-dotenv

# Загрузка переменных окружения (если работаете локально без Render.com)
# Предполагается, что у вас есть файл .env в том же каталоге
load_dotenv()

# Инициализация Cloudinary
try:
    cloudinary.config(
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key = os.getenv('CLOUDINARY_API_KEY'),
        api_secret = os.getenv('CLOUDINARY_API_SECRET'),
        secure = True
    )
    print("Cloudinary успешно инициализирован.")
    # Для проверки можете вывести некоторые конфиденциальные данные (ТОЛЬКО ДЛЯ ОТЛАДКИ, не для продакшена!)
    print(f"Cloud Name: {os.getenv('CLOUDINARY_CLOUD_NAME')}")
    # print(f"API Key: {os.getenv('CLOUDINARY_API_KEY')}") # Не рекомендуется выводить секреты
except Exception as e:
    print(f"Ошибка инициализации Cloudinary: {e}")

# Здесь можно добавить тестовый код для загрузки файла, чтобы убедиться, что все работает
# Например:
# try:
#     result = cloudinary.uploader.upload("path/to/your/local/image.jpg")
#     print(f"Загрузка успешна: {result['secure_url']}")
# except Exception as e:
#     print(f"Ошибка загрузки: {e}")