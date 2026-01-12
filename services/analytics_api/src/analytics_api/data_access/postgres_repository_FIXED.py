# This file contains the fixed write methods
# Copy the write_gold_products and write_gold_orders methods from here

def write_gold_products(self, client_id: str, products_data: list[dict]) -> int:
    """
    Write aggregated product metrics to analytics_gold_products table.

    Args:
        client_id: Client identifier
        products_data: List of dicts with product metrics

    Returns:
        Number of rows written
    """
    if not products_data:
        logger.debug(f"No product data to write for client {client_id}")
        return 0

    try:
        # Delete existing records for this client (refresh)
        delete_query = text("DELETE FROM analytics_gold_products WHERE client_id = :client_id")
        self.db_session.execute(delete_query, {"client_id": client_id})

        # Insert new records
        for product in products_data:
            # Handle NaN/Inf values for numeric columns
            avg_price = float(product.get("valor_unitario_medio", 0))
            if pd.isna(avg_price) or pd.isnull(avg_price) or not pd.isfinite(avg_price):
                avg_price = 0.0
            avg_price = min(max(avg_price, 0), 99999999.99)  # Clamp to decimal(10,2) range

            total_quantity = float(product.get("quantidade_total", 0))
            if pd.isna(total_quantity) or pd.isnull(total_quantity) or not pd.isfinite(total_quantity):
                total_quantity = 0.0
            total_quantity = min(max(total_quantity, 0), 99999999.99)

            total_revenue = float(product.get("receita_total", 0))
            if pd.isna(total_revenue) or pd.isnull(total_revenue) or not pd.isfinite(total_revenue):
                total_revenue = 0.0
            total_revenue = min(max(total_revenue, 0), 99999999.99)

            insert_query = text("""
                INSERT INTO analytics_gold_products (
                    client_id, product_name,
                    total_quantity_sold, total_revenue, avg_price, order_count,
                    period_type, calculated_at, created_at, updated_at
                ) VALUES (
                    :client_id, :product_name,
                    :total_quantity_sold, :total_revenue, :avg_price, :order_count,
                    :period_type, NOW(), NOW(), NOW()
                )
            """)
            self.db_session.execute(insert_query, {
                "client_id": client_id,
                "product_name": product.get("nome"),
                "total_quantity_sold": total_quantity,
                "total_revenue": total_revenue,
                "avg_price": avg_price,
                "order_count": int(product.get("num_pedidos_unicos", 0)),
                "period_type": "all_time"
            })

        self.db_session.commit()
        logger.info(f"Wrote {len(products_data)} product records to analytics_gold_products for {client_id}")
        return len(products_data)

    except Exception as e:
        self.db_session.rollback()
        logger.error(f"Failed to write product data: {e}", exc_info=True)
        return 0


def write_gold_orders(self, client_id: str, orders_metrics: dict) -> bool:
    """
    Write aggregated order metrics to analytics_gold_orders table.

    Args:
        client_id: Client identifier
        orders_metrics: Dict with order-level metrics

    Returns:
        True if successful, False otherwise
    """
    if not orders_metrics:
        logger.debug(f"No order data to write for client {client_id}")
        return False

    try:
        import json
        # Delete existing all_time record for this client
        delete_query = text(
            "DELETE FROM analytics_gold_orders WHERE client_id = :client_id AND period_type = :period_type"
        )
        self.db_session.execute(delete_query, {
            "client_id": client_id,
            "period_type": "all_time"
        })

        # Handle numeric values safely
        total_revenue = float(orders_metrics.get("total_revenue", 0))
        if pd.isna(total_revenue) or pd.isnull(total_revenue) or not pd.isfinite(total_revenue):
            total_revenue = 0.0
        total_revenue = min(max(total_revenue, 0), 99999999.99)

        avg_order_value = float(orders_metrics.get("avg_order_value", 0))
        if pd.isna(avg_order_value) or pd.isnull(avg_order_value) or not pd.isfinite(avg_order_value):
            avg_order_value = 0.0
        avg_order_value = min(max(avg_order_value, 0), 99999999.99)

        # Convert by_status dict to JSON string for JSONB storage
        by_status_json = json.dumps({})  # Empty for now

        # Insert new record
        insert_query = text("""
            INSERT INTO analytics_gold_orders (
                client_id,
                total_orders, total_revenue, avg_order_value,
                by_status,
                period_type, calculated_at, created_at, updated_at
            ) VALUES (
                :client_id,
                :total_orders, :total_revenue, :avg_order_value,
                :by_status::jsonb,
                :period_type, NOW(), NOW(), NOW()
            )
        """)
        self.db_session.execute(insert_query, {
            "client_id": client_id,
            "total_orders": int(orders_metrics.get("total_orders", 0)),
            "total_revenue": total_revenue,
            "avg_order_value": avg_order_value,
            "by_status": by_status_json,
            "period_type": "all_time"
        })

        self.db_session.commit()
        logger.info(f"Wrote order metrics to analytics_gold_orders for {client_id}")
        return True

    except Exception as e:
        self.db_session.rollback()
        logger.error(f"Failed to write order data: {e}", exc_info=True)
        return False
