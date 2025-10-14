from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Clients API"
    PROJECT_VERSION: str = "0.1.0"
    SERVICE_NAME: str = "clients-api"

    # Chave para criptografar/descriptografar credenciais (deve ser gerada via Fernet)
    CREDENTIALS_ENCRYPTION_KEY: str

    # Configuração do Pydantic para carregar de um arquivo .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

settings = Settings()