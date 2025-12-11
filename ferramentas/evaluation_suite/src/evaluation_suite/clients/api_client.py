import httpx
from loguru import logger

# Importaremos a configuração centralizada que criaremos a seguir
# from ..core.config import settings

class APIClient:
    """
    Um cliente HTTP genérico e assíncrono para interagir com as APIs da Vizu.
    Projetado para ser configurável e reutilizável.
    """

    def __init__(self, base_url: str, api_key: str = None):
        """
        Inicializa o cliente com a URL base da API alvo.

        Args:
            base_url: A URL raiz da API (ex: "http://atendente_api:8000").
            api_key: Chave de API para autenticação, se necessário.
        """
        if not base_url:
            raise ValueError("A URL base da API é obrigatória.")

        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["X-API-KEY"] = api_key

        # Usamos AsyncClient para performance e para facilitar os testes com mocks.
        self._client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=30.0)
        logger.info(f"APIClient inicializado para a base URL: {self.base_url}")

    async def send_message(self, clientevizu_id: str, message: str) -> None:
        """
        Envia uma mensagem para o endpoint padrão do atendente.

        Args:
            clientevizu_id: O ID do Cliente Vizu para a simulação.
            message: A mensagem a ser enviada.

        Raises:
            httpx.HTTPStatusError: Se a API retornar um código de erro (4xx ou 5xx).
        """
        endpoint = "/atendente/"
        payload = {
            "clientevizu_id": clientevizu_id,
            "mensagem": message,
        }

        try:
            logger.debug(f"Enviando POST para {self.base_url}{endpoint} com payload: {payload}")
            response = await self._client.post(endpoint, json=payload)

            # Lança uma exceção para respostas de erro, o que interromperá
            # a execução se a API estiver instável.
            response.raise_for_status()

            logger.success(
                f"Mensagem enviada com sucesso para clientevizu_id {clientevizu_id}. "
                f"Status: {response.status_code}"
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Erro de HTTP ao chamar a API: {e.response.status_code} "
                f"Response: {e.response.text}"
            )
            # Propagamos a exceção para que o orquestrador possa tratá-la.
            raise
        except httpx.RequestError as e:
            logger.error(f"Erro de conexão ao tentar acessar a API em {e.request.url!r}.")
            raise

    async def close(self):
        """Fecha a sessão do cliente HTTP."""
        await self._client.aclose()
        logger.info("Sessão do APIClient fechada.")

# Exemplo de como seria instanciado (isso irá para o orquestrador):
#
# from evaluation_suite.clients.assistant_client import APIClient
#
# # A URL viria de uma variável de ambiente através do nosso arquivo de config
# ASSISTANT_API_URL = "http://atendente_api:8000"
#
# async def main():
#     client = APIClient(base_url=ASSISTANT_API_URL)
#     try:
#         await client.send_message(
#             clientevizu_id="c3a4b1-e2d3-f4a5-b6c7-d8e9f0a1b2c3",
#             message="Qual o status do meu pedido?"
#         )
#     finally:
#         await client.close()
