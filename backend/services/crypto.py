"""Шифрование sensitive данных at rest (Fernet)."""
import json

try:
    from cryptography.fernet import Fernet, InvalidToken
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False

from config import settings


def _get_cipher():
    if not _CRYPTO_AVAILABLE:
        return None
    key = settings.encryption_key.strip()
    if not key:
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        return None


def encrypt_json(data: dict) -> dict:
    """Шифрует JSON-словарь, возвращает {'_enc': '<base64>'}. При отсутствии ключа — возвращает как есть."""
    cipher = _get_cipher()
    if cipher is None:
        return data
    plaintext = json.dumps(data, ensure_ascii=False).encode()
    return {"_enc": cipher.encrypt(plaintext).decode()}


def decrypt_json(data: dict) -> dict:
    """Расшифровывает {'_enc': '...'} обратно в словарь. Если не зашифровано — возвращает как есть."""
    if not isinstance(data, dict) or "_enc" not in data:
        return data
    cipher = _get_cipher()
    if cipher is None:
        return data
    try:
        plaintext = cipher.decrypt(data["_enc"].encode())
        return json.loads(plaintext)
    except Exception:
        return data
