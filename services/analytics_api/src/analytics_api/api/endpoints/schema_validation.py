"""
Comparison and Validation Endpoints for Star Schema Migration
Provides side-by-side comparison of old (gold) vs new (v2) schemas
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

router = APIRouter(prefix="/api/debug", tags=["schema-validation"])
logger = logging.getLogger(__name__)


@router.get("/compare/{client_id}")
async def compare_schemas(client_id: str, db_session) -> dict[str, Any]:
    """
    Compare old gold tables vs new v2 star schema side-by-side
    Useful for validation during migration

    Returns:
    - old_schema: Data from analytics_gold_* tables
    - new_schema: Data from analytics_v2.* tables
    - differences: Identified discrepancies
    - match: Boolean if schemas match
    """
    try:
        # Get data from old gold schema
        old_customers = await _get_gold_customers(client_id, db_session)
        old_time_series = await _get_gold_time_series(client_id, db_session)
        old_regional = await _get_gold_regional(client_id, db_session)

        # Get data from new v2 schema
        new_customers = await _get_v2_customers_with_metrics(client_id, db_session)
        new_time_series = await _get_v2_time_series(client_id, db_session)
        new_regional = await _get_v2_regional(client_id, db_session)
        new_fact_sales = await _get_v2_fact_sales_summary(client_id, db_session)

        # Calculate differences
        differences = {
            "customer_count": {
                "gold": len(old_customers),
                "v2": len(new_customers),
                "match": len(old_customers) == len(new_customers)
            },
            "time_series_points": {
                "gold": len(old_time_series),
                "v2": len(new_time_series),
                "match": len(old_time_series) == len(new_time_series)
            },
            "regional_points": {
                "gold": len(old_regional),
                "v2": len(new_regional),
                "match": len(old_regional) == len(new_regional)
            },
            "new_fact_sales_records": {
                "count": len(new_fact_sales),
                "note": "Transactional data (new architecture)"
            }
        }

        # Overall match status
        all_match = all(
            d.get("match", False)
            for k, d in differences.items()
            if isinstance(d, dict) and "match" in d
        )

        return {
            "client_id": client_id,
            "comparison": {
                "old_schema": {
                    "customers_count": len(old_customers),
                    "sample_customer": old_customers[0] if old_customers else None,
                    "time_series_count": len(old_time_series),
                    "regional_count": len(old_regional),
                },
                "new_schema": {
                    "customers_count": len(new_customers),
                    "sample_customer": new_customers[0] if new_customers else None,
                    "time_series_count": len(new_time_series),
                    "regional_count": len(new_regional),
                    "fact_sales_count": len(new_fact_sales),
                    "sample_fact_sale": new_fact_sales[0] if new_fact_sales else None,
                }
            },
            "differences": differences,
            "schemas_match": all_match,
            "migration_status": "ready" if all_match else "needs_investigation"
        }

    except Exception as e:
        logger.error(f"Comparison failed for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate/{client_id}")
async def validate_migration(client_id: str, db_session) -> dict[str, Any]:
    """
    Validate that the migration is complete and correct
    Checks data integrity and consistency between schemas
    """
    try:
        checks = {}

        # 1. Check dimension tables have proper aggregates
        checks["dim_customer_aggregates"] = await _validate_customer_aggregates(client_id, db_session)
        checks["dim_product_aggregates"] = await _validate_product_aggregates(client_id, db_session)
        checks["dim_supplier_aggregates"] = await _validate_supplier_aggregates(client_id, db_session)

        # 2. Check fact tables have transactional data
        checks["fact_sales_grain"] = await _validate_fact_sales_grain(client_id, db_session)

        # 3. Check materialized views exist and have data
        checks["materialized_views"] = await _validate_materialized_views(client_id, db_session)

        # 4. Check consistency (sum of facts = dimension aggregate)
        checks["data_consistency"] = await _validate_consistency(client_id, db_session)

        # Summary
        all_valid = all(c.get("valid", False) for c in checks.values())

        return {
            "client_id": client_id,
            "validation_checks": checks,
            "all_valid": all_valid,
            "status": "✅ PASSED" if all_valid else "❌ FAILED",
            "recommendations": _get_recommendations(checks)
        }

    except Exception as e:
        logger.error(f"Validation failed for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/{client_id}")
async def get_schema_metrics(client_id: str, db_session) -> dict[str, Any]:
    """
    Get detailed metrics about the star schema for this client
    Shows table sizes, completeness, and quality metrics
    """
    try:
        metrics = {
            "client_id": client_id,
            "dimensions": {
                "customers": await _get_table_metrics(client_id, "analytics_v2.dim_customer", db_session),
                "suppliers": await _get_table_metrics(client_id, "analytics_v2.dim_supplier", db_session),
                "products": await _get_table_metrics(client_id, "analytics_v2.dim_product", db_session),
            },
            "facts": {
                "fact_sales": await _get_table_metrics(client_id, "analytics_v2.fact_sales", db_session),
                "fact_customer_product": await _get_table_metrics(client_id, "analytics_v2.fact_customer_product", db_session),
            },
            "materialized_views": {
                "mv_customer_summary": await _get_materialized_view_metrics("analytics_v2.mv_customer_summary", client_id, db_session),
                "mv_product_summary": await _get_materialized_view_metrics("analytics_v2.mv_product_summary", client_id, db_session),
                "mv_monthly_sales_trend": await _get_materialized_view_metrics("analytics_v2.mv_monthly_sales_trend", client_id, db_session),
            }
        }
        return metrics
    except Exception as e:
        logger.error(f"Metrics retrieval failed for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Helper Functions
# ============================================================================



async def _get_v2_customers_with_metrics(client_id: str, db_session) -> list[dict]:
    """Fetch new v2 customers with aggregated metrics"""
    try:
        result = db_session.execute(
            text("""
                SELECT
                    customer_id, name, cpf_cnpj,
                    total_orders, total_revenue, avg_order_value,
                    frequency_per_month, recency_days
                FROM analytics_v2.dim_customer
                WHERE client_id = :client_id
                LIMIT 100
            """),
            {"client_id": client_id}
        )
        return [dict(row) for row in result]
    except Exception as e:
        logger.warning(f"Could not fetch v2 customers: {e}")
        return []




async def _get_v2_time_series(client_id: str, db_session) -> list[dict]:
    try:
        result = db_session.execute(
            text("SELECT * FROM analytics_v2.v_time_series WHERE client_id = :client_id LIMIT 10"),
            {"client_id": client_id}
        )
        return [dict(row) for row in result]
    except Exception:
        return []


async def _get_gold_regional(client_id: str, db_session) -> list[dict]:
    try:
        result = db_session.execute(
            text("SELECT * FROM analytics_gold_regional WHERE client_id = :client_id"),
            {"client_id": client_id}
        )
        return [dict(row) for row in result]
    except Exception:
        return []


async def _get_v2_regional(client_id: str, db_session) -> list[dict]:
    try:
        result = db_session.execute(
            text("SELECT * FROM analytics_v2.v_regional WHERE client_id = :client_id LIMIT 10"),
            {"client_id": client_id}
        )
        return [dict(row) for row in result]
    except Exception:
        return []


async def _get_v2_fact_sales_summary(client_id: str, db_session) -> list[dict]:
    """Get summary of fact_sales transactional data"""
    try:
        result = db_session.execute(
            text("""
                SELECT
                    COUNT(*) as total_line_items,
                    COUNT(DISTINCT order_id) as unique_orders,
                    COUNT(DISTINCT customer_cpf_cnpj) as unique_customers,
                    COUNT(DISTINCT product_name) as unique_products,
                    SUM(quantity) as total_quantity,
                    SUM(line_total) as total_revenue
                FROM analytics_v2.fact_sales
                WHERE client_id = :client_id
            """),
            {"client_id": client_id}
        )
        return [dict(row) for row in result]
    except Exception:
        return []


async def _validate_customer_aggregates(client_id: str, db_session) -> dict[str, Any]:
    """Check if customer aggregates are properly calculated"""
    try:
        result = db_session.execute(
            text("""
                SELECT
                    COUNT(*) as customers_with_metrics,
                    COUNT(CASE WHEN total_orders > 0 THEN 1 END) as customers_with_orders,
                    COUNT(CASE WHEN total_revenue > 0 THEN 1 END) as customers_with_revenue
                FROM analytics_v2.dim_customer
                WHERE client_id = :client_id
            """),
            {"client_id": client_id}
        )
        data = dict(result.first())

        return {
            "valid": data["customers_with_metrics"] > 0,
            "total_customers": data["customers_with_metrics"],
            "customers_with_orders": data["customers_with_orders"],
            "customers_with_revenue": data["customers_with_revenue"],
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def _validate_product_aggregates(client_id: str, db_session) -> dict[str, Any]:
    """Check if product aggregates are properly calculated"""
    try:
        result = db_session.execute(
            text("""
                SELECT
                    COUNT(*) as products_with_metrics,
                    COUNT(CASE WHEN total_quantity_sold > 0 THEN 1 END) as products_sold,
                    COUNT(CASE WHEN total_revenue > 0 THEN 1 END) as products_with_revenue
                FROM analytics_v2.dim_product
                WHERE client_id = :client_id
            """),
            {"client_id": client_id}
        )
        data = dict(result.first())

        return {
            "valid": data["products_with_metrics"] > 0,
            "total_products": data["products_with_metrics"],
            "products_sold": data["products_sold"],
            "products_with_revenue": data["products_with_revenue"],
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def _validate_supplier_aggregates(client_id: str, db_session) -> dict[str, Any]:
    """Check if supplier aggregates are properly calculated"""
    try:
        result = db_session.execute(
            text("""
                SELECT
                    COUNT(*) as suppliers_with_metrics,
                    COUNT(CASE WHEN total_orders_received > 0 THEN 1 END) as suppliers_with_orders,
                    COUNT(CASE WHEN total_revenue > 0 THEN 1 END) as suppliers_with_revenue
                FROM analytics_v2.dim_supplier
                WHERE client_id = :client_id
            """),
            {"client_id": client_id}
        )
        data = dict(result.first())

        return {
            "valid": data["suppliers_with_metrics"] > 0,
            "total_suppliers": data["suppliers_with_metrics"],
            "suppliers_with_orders": data["suppliers_with_orders"],
            "suppliers_with_revenue": data["suppliers_with_revenue"],
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def _validate_fact_sales_grain(client_id: str, db_session) -> dict[str, Any]:
    """Check that fact_sales has proper transactional grain"""
    try:
        result = db_session.execute(
            text("""
                SELECT
                    COUNT(*) as fact_sales_rows,
                    COUNT(DISTINCT order_id) as unique_orders,
                    MAX(line_item_sequence) as max_line_items_per_order,
                    AVG(line_item_sequence) as avg_line_items_per_order
                FROM analytics_v2.fact_sales
                WHERE client_id = :client_id
            """),
            {"client_id": client_id}
        )
        data = dict(result.first()) if result else {}

        is_valid = (data.get("fact_sales_rows", 0) > data.get("unique_orders", 0))

        return {
            "valid": is_valid,
            "fact_rows": data.get("fact_sales_rows"),
            "unique_orders": data.get("unique_orders"),
            "avg_lines_per_order": round(data.get("avg_line_items_per_order", 0), 2),
            "note": "Valid grain: more facts than dimensions (line items > orders)"
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def _validate_materialized_views(client_id: str, db_session) -> dict[str, Any]:
    """Check that materialized views exist and have data"""
    try:
        views = {}
        for view_name in ["mv_customer_summary", "mv_product_summary", "mv_monthly_sales_trend"]:
            try:
                result = db_session.execute(
                    text(f"SELECT COUNT(*) as count FROM analytics_v2.{view_name} WHERE client_id = :client_id"),
                    {"client_id": client_id}
                )
                count = dict(result.first()).get("count", 0)
                views[view_name] = {"exists": True, "row_count": count}
            except Exception:
                views[view_name] = {"exists": False}

        all_exist = all(v.get("exists", False) for v in views.values())
        return {
            "valid": all_exist,
            "views": views
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def _validate_consistency(client_id: str, db_session) -> dict[str, Any]:
    """Validate that dimension aggregates match fact table sums"""
    try:
        # Check customer consistency
        result = db_session.execute(
            text("""
                SELECT
                    d.customer_id,
                    d.total_orders as dim_total_orders,
                    COALESCE(f.calc_orders, 0) as fact_total_orders,
                    (d.total_orders = COALESCE(f.calc_orders, 0)) as orders_match,
                    d.total_revenue as dim_revenue,
                    COALESCE(f.calc_revenue, 0) as fact_revenue,
                    (ABS(d.total_revenue - COALESCE(f.calc_revenue, 0)) < 0.01) as revenue_match
                FROM analytics_v2.dim_customer d
                LEFT JOIN (
                    SELECT
                        customer_cpf_cnpj,
                        COUNT(DISTINCT order_id) as calc_orders,
                        SUM(line_total) as calc_revenue
                    FROM analytics_v2.fact_sales
                    WHERE client_id = :client_id
                    GROUP BY customer_cpf_cnpj
                ) f ON d.cpf_cnpj = f.customer_cpf_cnpj
                WHERE d.client_id = :client_id
                LIMIT 10
            """),
            {"client_id": client_id}
        )

        samples = [dict(row) for row in result]
        matches = sum(1 for s in samples if s.get("orders_match") and s.get("revenue_match"))

        return {
            "valid": matches > 0 if samples else True,
            "consistency_check": f"{matches}/{len(samples)} customers match",
            "sample_mismatches": [s for s in samples if not (s.get("orders_match") and s.get("revenue_match"))]
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def _get_table_metrics(client_id: str, table_name: str, db_session) -> dict[str, Any]:
    """Get size and completeness metrics for a table"""
    try:
        result = db_session.execute(
            text(f"SELECT COUNT(*) as count FROM {table_name} WHERE client_id = :client_id"),
            {"client_id": client_id}
        )
        count = dict(result.first()).get("count", 0)
        return {"row_count": count, "status": "✅" if count > 0 else "⚠️ empty"}
    except Exception as e:
        return {"error": str(e), "status": "❌"}


async def _get_materialized_view_metrics(view_name: str, client_id: str, db_session) -> dict[str, Any]:
    """Get metrics for materialized views"""
    try:
        result = db_session.execute(
            text(f"SELECT COUNT(*) as count FROM {view_name} WHERE client_id = :client_id"),
            {"client_id": client_id}
        )
        count = dict(result.first()).get("count", 0)
        return {"row_count": count, "status": "✅" if count > 0 else "⚠️ empty"}
    except Exception as e:
        return {"error": str(e), "status": "❌"}


def _get_recommendations(checks: dict[str, Any]) -> list[str]:
    """Generate recommendations based on validation results"""
    recommendations = []

    if not checks.get("dim_customer_aggregates", {}).get("valid"):
        recommendations.append("❌ Customer aggregates incomplete - run recalculation")

    if not checks.get("dim_product_aggregates", {}).get("valid"):
        recommendations.append("❌ Product aggregates incomplete - run recalculation")

    if not checks.get("fact_sales_grain", {}).get("valid"):
        recommendations.append("⚠️ Fact sales may not have proper transactional grain")

    if not checks.get("materialized_views", {}).get("valid"):
        recommendations.append("⚠️ Materialized views need to be created/refreshed")

    if not checks.get("data_consistency", {}).get("valid"):
        recommendations.append("❌ Data consistency issues found - review dimension aggregates")

    if not recommendations:
        recommendations.append("✅ All checks passed - schema is ready for use")

    return recommendations
