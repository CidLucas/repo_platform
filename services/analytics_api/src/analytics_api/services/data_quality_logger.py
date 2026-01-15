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
    def log_dataframe_describe(df: pd.DataFrame, stage: str, table_name: str = "") -> None:
        """
        Log detailed describe() statistics for a DataFrame at a specific processing stage.

        Args:
            df: DataFrame to analyze
            stage: Processing stage name (e.g., "Silver Input", "After Aggregation", "Before Write")
            table_name: Optional table name for context
        """
        if df.empty:
            logger.info(f"📊 [{stage}] {table_name} - Empty DataFrame")
            return

        prefix = f"[{stage}]" + (f" {table_name}" if table_name else "")

        logger.info(f"📊 {prefix} - Shape: {df.shape} (rows × columns)")

        # Describe numeric columns
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns
        if len(numeric_cols) > 0:
            desc = df[numeric_cols].describe()
            logger.info(f"   Numeric Statistics:")
            logger.info(f"   {'Column':<30} {'Count':<10} {'Mean':<12} {'Min':<12} {'Max':<12} {'Zeros':<8}")
            logger.info(f"   {'-'*85}")

            for col in numeric_cols[:10]:  # Limit to first 10 numeric columns
                stats = desc[col]
                zero_count = (df[col] == 0).sum()
                zero_pct = (zero_count / len(df)) * 100 if len(df) > 0 else 0

                logger.info(
                    f"   {col:<30} "
                    f"{int(stats['count']):<10} "
                    f"{stats['mean']:<12.2f} "
                    f"{stats['min']:<12.2f} "
                    f"{stats['max']:<12.2f} "
                    f"{zero_count} ({zero_pct:.0f}%)"
                )

        # Date columns
        date_cols = df.select_dtypes(include=['datetime64']).columns
        if len(date_cols) > 0:
            logger.info(f"   Date Columns:")
            for col in date_cols:
                min_date = df[col].min()
                max_date = df[col].max()
                null_count = df[col].isnull().sum()
                logger.info(f"   {col:<30} Range: {min_date} to {max_date} (nulls: {null_count})")

        # Object/String columns
        object_cols = df.select_dtypes(include=['object', 'string']).columns
        if len(object_cols) > 0:
            logger.info(f"   Categorical Columns:")
            for col in object_cols[:5]:  # Limit to first 5
                unique_count = df[col].nunique()
                null_count = df[col].isnull().sum()
                logger.info(f"   {col:<30} Unique: {unique_count}, Nulls: {null_count}")

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
