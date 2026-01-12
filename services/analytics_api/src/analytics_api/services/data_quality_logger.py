"""
Data Quality Logger - Validação de dados antes de persistir no Gold.

Gera relatórios de qualidade dos dados agregados:
- Contagem de nulos por coluna
- Contagem de zeros por coluna
- Tipos de dados
- Estatísticas básicas
"""
import logging
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DataQualityLogger:
    """Logs data quality metrics for Gold table writes."""

    @staticmethod
    def log_dataframe_quality(df: pd.DataFrame, table_name: str, client_id: str) -> Dict[str, Any]:
        """
        Analisa qualidade dos dados de um DataFrame antes de persistir.

        Returns:
            dict com estatísticas de qualidade
        """
        if df.empty:
            logger.warning(f"⚠️  [{table_name}] Empty DataFrame - no quality check")
            return {"status": "empty", "rows": 0}

        stats = {
            "table": table_name,
            "client_id": client_id,
            "rows": len(df),
            "columns": len(df.columns),
            "null_counts": {},
            "zero_counts": {},
            "datatypes": {},
        }

        # Count nulls per column
        null_counts = df.isnull().sum()
        stats["null_counts"] = {col: int(count) for col, count in null_counts.items() if count > 0}

        # Count zeros per column (only numeric columns)
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns
        zero_counts = (df[numeric_cols] == 0).sum()
        stats["zero_counts"] = {col: int(count) for col, count in zero_counts.items() if count > 0}

        # Datatypes
        stats["datatypes"] = {col: str(dtype) for col, dtype in df.dtypes.items()}

        # Log summary
        logger.info(f"📊 [{table_name}] Data Quality Report:")
        logger.info(f"   Rows: {stats['rows']}, Columns: {stats['columns']}")

        if stats["null_counts"]:
            logger.warning(f"   ⚠️  Null values found:")
            for col, count in sorted(stats["null_counts"].items(), key=lambda x: x[1], reverse=True)[:5]:
                pct = (count / stats['rows']) * 100
                logger.warning(f"      - {col}: {count}/{stats['rows']} ({pct:.1f}%)")
        else:
            logger.info(f"   ✅ No null values")

        if stats["zero_counts"]:
            # Only warn if >50% are zeros
            high_zero_cols = {col: count for col, count in stats["zero_counts"].items()
                            if (count / stats['rows']) > 0.5}
            if high_zero_cols:
                logger.warning(f"   ⚠️  High zero counts (>50%):")
                for col, count in sorted(high_zero_cols.items(), key=lambda x: x[1], reverse=True)[:5]:
                    pct = (count / stats['rows']) * 100
                    logger.warning(f"      - {col}: {count}/{stats['rows']} ({pct:.1f}%)")

        return stats

    @staticmethod
    def log_dict_quality(data: Dict[str, Any], table_name: str, client_id: str) -> Dict[str, Any]:
        """Analisa qualidade de um dicionário de métricas."""
        stats = {
            "table": table_name,
            "client_id": client_id,
            "fields": len(data),
            "null_fields": [],
            "zero_fields": [],
            "datatypes": {}
        }

        for key, value in data.items():
            if value is None:
                stats["null_fields"].append(key)
            elif isinstance(value, (int, float)) and value == 0:
                stats["zero_fields"].append(key)
            stats["datatypes"][key] = type(value).__name__

        logger.info(f"📊 [{table_name}] Metrics Quality:")
        logger.info(f"   Fields: {stats['fields']}")
        if stats["null_fields"]:
            logger.warning(f"   ⚠️  Null: {', '.join(stats['null_fields'])}")
        if stats["zero_fields"]:
            logger.info(f"   Zero values: {', '.join(stats['zero_fields'][:5])}")

        return stats
