from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Gerencia as configurações da aplicação, carregando-as de variáveis de ambiente.
    """
    # Carrega as variáveis a partir de um arquivo .env, se existir.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # URL da API do Atendente que será alvo dos testes.
    # Exemplo: "http://atendente_api:8000"
    ASSISTANT_API_URL: str = "http://localhost:8001"

    # Chave de API para a API do Atendente (se aplicável).
    ASSISTANT_API_KEY: str | None = None

    # String de conexão com o banco de dados.
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/vizu_db"


# Instância única das configurações que será importada por toda a aplicação.
settings = Settings()
