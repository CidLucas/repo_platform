# src/analytics_api/data_access/postgres_repository.py
import logging
from datetime import datetime
from typing import Any

import pandas as pd
from analytics_api.core.analytics_mapping import get_silver_table_name
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class PostgresRepository:
    """
    Camada de acesso aos dados Prata (exclusivamente do nosso Postgres).
    (Corrigido para usar Session injetada)
    """
    # ALTERADO: Recebe a Session no construtor
    def __init__(self, db_session: Session):
        self.db_session = db_session # Armazena a sessão

    def get_silver_dataframe(self, client_id: str) -> pd.DataFrame:
        """
        Busca TODOS os dados da tabela Prata do cliente e carrega em
        um DataFrame Pandas para processamento em memória.
        """
        table_name = get_silver_table_name(client_id)
        query = f"SELECT * FROM {table_name}"

        logger.info(f"Buscando dados Prata da tabela: {table_name}")

        try:
            df = pd.read_sql(query, self.db_session.bind)
            logger.info(f"{len(df)} linhas carregadas da camada Prata.")
            return df
        except Exception as e:
            logger.error(f"Falha ao buscar dados da tabela Prata '{table_name}': {e}")
            raise

    def get_order_metrics_by_date_range(
        self,
        client_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict[str, Any]:
        """
        Calcula métricas de pedidos para um range de datas.
        Returns:
            dict com total, revenue, avg_order_value, by_status
        """
        table_name = get_silver_table_name(client_id)
        query = text(f"""
            SELECT
                COUNT(DISTINCT order_id) as total,
                COALESCE(SUM(valor_total_emitter), 0) as revenue,
                COALESCE(AVG(valor_total_emitter), 0) as avg_order_value
            FROM {table_name}
            WHERE data_transacao >= :start_date
              AND data_transacao < :end_date
        """)
        status_query = text(f"""
            SELECT
                COALESCE(status, 'unknown') as status,
                COUNT(DISTINCT order_id) as count
            FROM {table_name}
            WHERE data_transacao >= :start_date
              AND data_transacao < :end_date
            GROUP BY status
        """)
        try:
            result = self.db_session.execute(
                query,
                {"start_date": start_date, "end_date": end_date}
            ).fetchone()
            status_result = self.db_session.execute(
                status_query,
                {"start_date": start_date, "end_date": end_date}
            ).fetchall()
            by_status = {row.status: row.count for row in status_result}
            return {
                "total": result.total or 0,
                "revenue": float(result.revenue or 0),
                "avg_order_value": float(result.avg_order_value or 0),
                "by_status": by_status
            }
        except Exception as e:
            logger.error(f"Erro ao buscar métricas de pedidos: {e}")
            return {"total": 0, "revenue": 0.0, "avg_order_value": 0.0, "by_status": {}}

    def get_product_metrics_by_date_range(
        self,
        client_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict[str, Any]:
        """Calcula métricas de produtos para um range de datas."""
        table_name = get_silver_table_name(client_id)
        query = text(f"""
            SELECT
                COALESCE(SUM(quantidade), 0) as total_sold,
                COUNT(DISTINCT raw_product_description) as unique_products,
                COALESCE(AVG(valor_unitario), 0) as avg_price
            FROM {table_name}
            WHERE data_transacao >= :start_date
              AND data_transacao < :end_date
        """)
        top_sellers_query = text(f"""
            SELECT
                raw_product_description as name,
                SUM(quantidade) as quantity,
                SUM(valor_total_emitter) as revenue
            FROM {table_name}
            WHERE data_transacao >= :start_date
              AND data_transacao < :end_date
            GROUP BY raw_product_description
            ORDER BY revenue DESC
            LIMIT 10
        """)
        try:
            result = self.db_session.execute(
                query,
                {"start_date": start_date, "end_date": end_date}
            ).fetchone()
            top_sellers = self.db_session.execute(
                top_sellers_query,
                {"start_date": start_date, "end_date": end_date}
            ).fetchall()
            return {
                "total_sold": int(result.total_sold or 0),
                "unique_products": result.unique_products or 0,
                "avg_price": float(result.avg_price or 0),
                "top_sellers": [
                    {"name": r.name, "quantity": int(r.quantity), "revenue": float(r.revenue)}
                    for r in top_sellers
                ],
                "low_stock_alerts": 0  # Placeholder - requer tabela de estoque
            }
        except Exception as e:
            logger.error(f"Erro ao buscar métricas de produtos: {e}")
            return {"total_sold": 0, "unique_products": 0, "avg_price": 0.0, "top_sellers": [], "low_stock_alerts": 0}

    def get_customer_metrics_by_date_range(
        self,
        client_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict[str, Any]:
        """Calcula métricas de clientes para um range de datas."""
        table_name = get_silver_table_name(client_id)
        query = text(f"""
            WITH customer_stats AS (
                SELECT
                    receiver_nome,
                    MIN(data_transacao) as first_order,
                    SUM(valor_total_emitter) as lifetime_value
                FROM {table_name}
                GROUP BY receiver_nome
            )
            SELECT
                COUNT(DISTINCT cs.receiver_nome) as total_active,
                COUNT(DISTINCT CASE
                    WHEN cs.first_order >= :start_date THEN cs.receiver_nome
                END) as new_customers,
                COUNT(DISTINCT CASE
                    WHEN cs.first_order < :start_date THEN cs.receiver_nome
                END) as returning_customers,
                COALESCE(AVG(cs.lifetime_value), 0) as avg_lifetime_value
            FROM customer_stats cs
            INNER JOIN {table_name} t ON cs.receiver_nome = t.receiver_nome
            WHERE t.data_transacao >= :start_date
              AND t.data_transacao < :end_date
        """)
        try:
            result = self.db_session.execute(
                query,
                {"start_date": start_date, "end_date": end_date}
            ).fetchone()
            return {
                "total_active": result.total_active or 0,
                "new_customers": result.new_customers or 0,
                "returning_customers": result.returning_customers or 0,
                "avg_lifetime_value": float(result.avg_lifetime_value or 0)
            }
        except Exception as e:
            logger.error(f"Erro ao buscar métricas de clientes: {e}")
            return {"total_active": 0, "new_customers": 0, "returning_customers": 0, "avg_lifetime_value": 0.0}

    def get_or_create_cliente_vizu_id(self, external_user_id: str) -> str:
        """
        Busca ou cria um cliente_vizu_id associado ao external_user_id (Supabase user id).
        Retorna o cliente_vizu_id (UUID em string).
        """
        # Exemplo: tabela clientes (id UUID, external_user_id TEXT UNIQUE)
        result = self.db_session.execute(
            text("""
                SELECT id FROM clientes WHERE external_user_id = :external_user_id
            """),
            {"external_user_id": external_user_id}
        ).fetchone()
        if result:
            return str(result.id)
        # Cria novo cliente
        new_id = self.db_session.execute(
            text("""
                INSERT INTO clientes (external_user_id) VALUES (:external_user_id) RETURNING id
            """),
            {"external_user_id": external_user_id}
        ).fetchone().id
        self.db_session.commit()
        return str(new_id)
