import io
from abc import ABC, abstractmethod


class BaseParser(ABC):
    """
    Interface (Classe Base Abstrata) para todos os parsers de arquivo.

    Define o contrato que todo parser (PDF, CSV, etc.) deve seguir.
    O método 'parse' recebe um objeto "file-like" (o arquivo baixado
    do GCS) e deve retornar o conteúdo textual extraído.
    """

    @abstractmethod
    def parse(self, file_stream: io.BytesIO) -> str:
        """
        Extrai o conteúdo textual de um stream de bytes de arquivo.

        Args:
            file_stream: O arquivo em memória (ex: io.BytesIO)
                         baixado do GCS.

        Returns:
            Uma string única contendo todo o texto extraído do arquivo.
        """
        pass
