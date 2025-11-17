import io
import logging
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from file_processing_worker.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)

class PDFParser(BaseParser):
    """
    Implementação concreta do BaseParser para extrair texto de ficheiros PDF.
    """

    def parse(self, file_stream: io.BytesIO) -> str:
        """
        Lê um stream de bytes de um ficheiro PDF e extrai o seu conteúdo textual.

        Args:
            file_stream: O ficheiro PDF em memória (io.BytesIO).

        Returns:
            Uma string única contendo o texto concatenado de todas as páginas.
            Retorna uma string vazia se o PDF não puder ser lido ou
            não contiver texto.
        """
        logger.info("Iniciando parsing de PDF...")

        try:
            # Garante que o ponteiro do stream está no início
            file_stream.seek(0)

            # Abre o PDF diretamente do stream em memória
            reader = PdfReader(file_stream)

            extracted_pages = []
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        extracted_pages.append(text)
                except Exception as e:
                    # Loga erro na extração de uma página específica, mas continua
                    logger.warning(f"Erro ao extrair texto da página {i} do PDF. Erro: {e}")

            if not extracted_pages:
                logger.warning("PDF processado, mas nenhum texto foi extraído.")
                return ""

            logger.info(f"Parsing de PDF concluído. {len(extracted_pages)} páginas extraídas.")
            # Junta o texto de todas as páginas com uma quebra de linha
            return "\n".join(extracted_pages)

        except PdfReadError as e:
            logger.error(f"Falha ao ler o ficheiro PDF. Pode estar corrompido ou encriptado. Erro: {e}")
            return ""
        except Exception as e:
            logger.error(f"Erro inesperado durante o parsing do PDF: {e}", exc_info=True)
            return ""