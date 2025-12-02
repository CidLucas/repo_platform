# services/clients_api/src/clients_api/core/security.py (VERSÃO FINAL E COMPLETA)

import secrets  # <-- PASSO 1: Adicionamos a biblioteca 'secrets' do Python.
import hashlib  # <-- PASSO 2: Adicionamos a biblioteca 'hashlib'.
from typing import Tuple
from cryptography.fernet import Fernet
from .config import settings

# ---------------------------------------------------------------------------
# SEÇÃO 1: CRIPTOGRAFIA DE CREDENCIAIS (Lógica que você já tinha)
# Esta parte permanece a mesma. É usada para criptografar/descriptografar dados.
# ---------------------------------------------------------------------------
try:
    fernet_key = settings.CREDENTIALS_ENCRYPTION_KEY.encode()
    cipher_suite = Fernet(fernet_key)
except Exception as e:
    raise RuntimeError(
        "CREDENTIALS_ENCRYPTION_KEY inválida. "
        "Certifique-se de que é uma chave Fernet válida e está no .env"
    ) from e

def encrypt_credential(value: str) -> str:
    """Criptografa um valor usando a chave Fernet global."""
    if not value:
        return value
    encrypted_value = cipher_suite.encrypt(value.encode())
    return encrypted_value.decode()

def decrypt_credential(encrypted_value: str) -> str:
    """Descriptografa um valor usando a chave Fernet global."""
    if not encrypted_value:
        return encrypted_value
    decrypted_value = cipher_suite.decrypt(encrypted_value.encode())
    return decrypted_value.decode()

# ---------------------------------------------------------------------------
# SEÇÃO 2: GERAÇÃO E HASHING DE API KEYS (Nova Lógica)
# Esta é a funcionalidade que estava faltando.
# ---------------------------------------------------------------------------

def get_password_hash(password: str) -> str:
    """
    PASSO 3: Criamos uma função para gerar um hash.
    Ela pega uma string (nossa API Key) e cria uma impressão digital
    SHA-256 dela. É uma via de mão única, para armazenamento seguro.
    """
    return hashlib.sha256(password.encode()).hexdigest()

def create_api_key() -> Tuple[str, str]:
    """
    PASSO 4: Criamos a função 'create_api_key' que estava faltando.
    Esta é a função que o client_service tentava importar.
    """
    # a. Usa a biblioteca 'secrets' para gerar uma chave aleatória e segura.
    #    'token_hex(32)' cria uma string de 64 caracteres hexadecimais.
    api_key = secrets.token_hex(32)

    # b. Usa nossa função de hash para criar a versão segura da chave para o banco.
    hashed_api_key = get_password_hash(api_key)

    # c. Retorna as duas versões. A original (api_key) será mostrada ao usuário
    #    apenas uma vez. A versão hasheada (hashed_api_key) será salva no banco.
    return api_key, hashed_api_key