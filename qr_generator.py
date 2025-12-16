import qrcode
from io import BytesIO
from PIL import Image
import os

# Опциональные зависимости для распознавания QR из фото
# Для установки: pip install pyzbar opencv-python numpy
try:
    from pyzbar import pyzbar
    import cv2
    import numpy as np
    QR_DECODE_AVAILABLE = True
except ImportError:
    QR_DECODE_AVAILABLE = False


async def generate_qr_code(user_id: int, username: str = None) -> BytesIO:
    """
    Генерирует QR код для пользователя
    """
    # Создаем директорию для QR кодов если её нет
    os.makedirs('qr_codes', exist_ok=True)
    
    # Данные для QR кода
    qr_data = f"KOREJAPY_USER_{user_id}"
    
    # Создаем QR код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    # Создаем изображение
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Сохраняем в память
    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    
    # Сохраняем также в файл для истории
    file_path = f'qr_codes/user_{user_id}.png'
    img.save(file_path)
    
    return img_io


def parse_qr_code(qr_data: str) -> dict:
    """
    Парсит данные из QR кода
    Возвращает user_id если QR код валидный
    """
    try:
        if qr_data.startswith("KOREJAPY_USER_"):
            user_id = int(qr_data.replace("KOREJAPY_USER_", ""))
            return {"valid": True, "user_id": user_id}
        return {"valid": False, "error": "Неверный формат QR кода"}
    except ValueError:
        return {"valid": False, "error": "Неверный формат данных"}


def decode_qr_from_image(image_bytes: bytes) -> dict:
    """
    Декодирует QR код из изображения
    """
    if not QR_DECODE_AVAILABLE:
        return {
            "valid": False, 
            "error": "Распознавание QR из фото недоступно. Установите: pip install pyzbar opencv-python numpy"
        }
    
    try:
        # Конвертируем bytes в numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        # Декодируем изображение
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {"valid": False, "error": "Не удалось декодировать изображение"}
        
        # Распознаем QR коды
        decoded_objects = pyzbar.decode(img)
        
        if not decoded_objects:
            return {"valid": False, "error": "QR код не найден на изображении"}
        
        # Берем первый найденный QR код
        qr_data = decoded_objects[0].data.decode('utf-8')
        return parse_qr_code(qr_data)
    
    except Exception as e:
        return {"valid": False, "error": f"Ошибка обработки: {str(e)}"}

