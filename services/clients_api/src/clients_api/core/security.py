import os
from cryptography.fernet import Fernet
from .config import settings

# Carrega a chave de criptografia a partir das configurações.
# A chave DEVE ser uma string de 32 bytes codificada em URL-safe base64.
# Em um ambiente real, esta chave viria do Secret Manager.
try:
    fernet_key = settings.CREDENTIALS_ENCRYPTION_KEY.encode()
    cipher_suite = Fernet(fernet_key)
except Exception as e:
    raise RuntimeError(
        "CREDENTIALS_ENCRYPTION_KEY inválida. "
        "Certifique-se de que é uma chave Fernet válida e está no .env"
    ) from e

def encrypt_credential(value: str) -> str:
    """Criptografa um valor usando a chave global."""
    if not value:
        return value
    encrypted_value = cipher_suite.encrypt(value.encode())
    return encrypted_value.decode()

def decrypt_credential(encrypted_value: str) -> str:
    """Descriptografa um valor usando a chave global."""
    if not encrypted_value:
        return encrypted_value
    decrypted_value = cipher_suite.decrypt(encrypted_value.encode())
    return decrypted_value.decode()