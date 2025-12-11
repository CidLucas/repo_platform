"""CSV parser implementation using pandas."""

import io
import logging
from typing import BinaryIO

import pandas as pd

from vizu_parsers.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class CSVParser(BaseParser):
    """
    Parser for extracting text from CSV files using pandas.
    """

    def parse(self, file_stream: io.BytesIO | BinaryIO) -> str:
        """
        Read a CSV file stream and extract its textual content.

        Automatically detects the separator.

        Args:
            file_stream: The CSV file in memory (io.BytesIO) or file object.

        Returns:
            A string representation of the CSV content.
            Returns empty string if the CSV cannot be read.
        """
        logger.debug("Starting CSV parsing...")

        try:
            # Ensure stream pointer is at the beginning
            file_stream.seek(0)

            # Read CSV with auto-detection of separator
            # 'sep=None' activates pandas' automatic separator detection
            df = pd.read_csv(file_stream, sep=None, engine="python")

            if df.empty:
                logger.warning("CSV processed but is empty.")
                return ""

            # Convert DataFrame back to string
            # 'index=False' prevents pandas index from being included
            csv_string = df.to_string(index=False)

            logger.debug(f"CSV parsing complete. Extracted {len(df)} rows.")
            return csv_string

        except pd.errors.EmptyDataError:
            logger.warning("CSV processed but contains no data (EmptyDataError).")
            return ""
        except Exception as e:
            logger.error(
                f"Unexpected error during CSV parsing: {e}", exc_info=True
            )
            return ""
