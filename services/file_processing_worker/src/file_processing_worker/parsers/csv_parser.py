import io
import logging
import pandas as pd

from file_processing_worker.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)

class CSVParser(BaseParser):
    """
    Implementação concreta do BaseParser para extrair texto de ficheiros CSV.
    Utiliza o pandas para robustez na leitura.
    """

    def parse(self, file_stream: io.BytesIO) -> str:
        """
        Lê um stream de bytes de um ficheiro CSV e extrai o seu conteúdo textual.

        Tenta detetar automaticamente o separador.

        Args:
            file_stream: O ficheiro CSV em memória (io.BytesIO).

        Returns:
            Uma string única representando o conteúdo do CSV.
            Retorna uma string vazia se o CSV não puder ser lido.
        """
        logger.info("Iniciando parsing de CSV...")

        try:
            # Garante que o ponteiro do stream está no início
            file_stream.seek(0)

            # Tenta ler o CSV. O pandas é bom a inferir tipos,
            # mas podemos precisar de mais deteção de encoding/separador no futuro.
            # 'sep=None' ativa a deteção automática de separador do pandas.
            df = pd.read_csv(file_stream, sep=None, engine='python')

            if df.empty:
                logger.warning("CSV processado, mas está vazio.")
                return ""

            # Converte o DataFrame de volta para uma string
            # 'index=False' evita que o índice do pandas seja incluído no texto.
            csv_string = df.to_string(index=False)

            logger.info(f"Parsing de CSV concluído. Extraídas {len(df)} linhas.")
            return csv_string

        except pd.errors.EmptyDataError:
            logger.warning("CSV processado, mas não contém dados (EmptyDataError).")
            return ""
        except Exception as e:
            # 'Exception' genérico, pois o pandas pode lançar vários erros
            logger.error(f"Erro inesperado durante o parsing do CSV: {e}", exc_info=True)
            return ""