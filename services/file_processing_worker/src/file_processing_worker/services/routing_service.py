import logging
from typing import Dict, Type

from file_processing_worker.parsers.base_parser import BaseParser
from file_processing_worker.parsers.pdf_parser import PDFParser
from file_processing_worker.parsers.csv_parser import CSVParser

logger = logging.getLogger(__name__)

class RoutingService:
    """
    Serviço responsável por selecionar o 'parser' apropriado
    com base no tipo de conteúdo (MIME type) do ficheiro.
    """

    def __init__(self):
        """
        Inicializa o mapa de roteamento.
        Este mapa associa MIME types às classes de parser correspondentes.
        """
        # Padrão Vizu: Modularização via Roteamento de Implementação
        # Mapeia o MIME type (ou parte dele) à classe do parser.
        self._parser_map: Dict[str, Type[BaseParser]] = {
            "application/pdf": PDFParser,
            "text/csv": CSVParser,
            # (Podemos adicionar mais MIME types de CSV se necessário)
            "application/vnd.ms-excel": CSVParser,
        }
        logger.info(f"RoutingService inicializado com {len(self._parser_map)} parsers.")

    def get_parser(self, content_type: str) -> BaseParser | None:
        """
        Obtém uma instância do parser apropriado para o content_type fornecido.

        Args:
            content_type: O MIME type do ficheiro (ex: 'application/pdf').

        Returns:
            Uma instância de um BaseParser (ex: PDFParser()) se um parser
            compatível for encontrado, ou None se o tipo não for suportado.
        """

        # Procura por uma correspondência exata primeiro
        parser_class = self._parser_map.get(content_type)

        if parser_class:
            logger.info(f"Parser encontrado para o content_type '{content_type}': {parser_class.__name__}")
            return parser_class() # Retorna uma *nova instância* do parser

        # (Lógica futura: poderíamos tentar correspondência parcial,
        # ex: 'text/plain' poderia ser mapeado para um 'TextParser')

        logger.warning(f"Nenhum parser encontrado para o content_type: '{content_type}'")
        return None