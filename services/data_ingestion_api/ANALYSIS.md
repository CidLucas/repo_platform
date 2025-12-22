# Data Ingestion API - Flow Analysis & Optimization Opportunities

## Current Application Flow

### What the API Actually Does:

```
1. E-COMMERCE CONNECTORS (Shopify, VTEX, Loja Integrada)
   └─> httpx calls to e-commerce APIs
   └─> Returns JSON (converted to pandas DataFrame)
   └─> ❌ Uses pandas but doesn't need it!

2. BIGQUERY CONNECTOR (Enterprise)
   └─> google-cloud-bigquery client
   └─> Executes SQL queries
   └─> Returns data as pandas DataFrame
   └─> ✅ Actually needs pandas for BigQuery

3. PUB/SUB JOB PUBLISHER
   └─> google-cloud-pubsub
   └─> Publishes ingestion jobs to worker
   └─> ✅ Actually needs this
```

---

## Problem: Pandas is Used EVERYWHERE but Only NEEDED for BigQuery

### E-commerce Connectors (Shopify, VTEX, Loja Integrada)

**Current:**
```python
# ecommerce_base_connector.py:269
async def extract_data(...) -> AsyncGenerator[pd.DataFrame, None]:
    data = await self._get_products(...)  # Returns list[dict] from API
    df = pd.DataFrame(data)  # ❌ UNNECESSARY! Just converting JSON to DataFrame
    yield df
```

**What Actually Happens:**
1. Call Shopify API → Get JSON (list of dicts)
2. Convert to pandas DataFrame
3. Return DataFrame
4. Worker converts DataFrame back to JSON
5. Write JSON to Supabase

**WHY USE PANDAS HERE?** No reason! It's just transforming JSON → DataFrame → JSON

### BigQuery Connector

**Current:**
```python
# bigquery_connector.py:111
def _extract_sync(...) -> Generator[pd.DataFrame, None, None]:
    query_job = self._client.query(sql_query)
    for page in query_job.result(page_size=chunk_size):
        dataframe_chunk = pd.DataFrame(data, columns=column_names)
        yield dataframe_chunk  # ✅ Makes sense for BigQuery results
```

**Why BigQuery needs it:** BigQuery results are tabular data that benefits from DataFrame operations.

---

## Solution: Split into 2 Services

### Option 1: Lightweight E-commerce API (Recommended)

**Remove:**
- `pandas` (saves ~47MB)
- `pyarrow` (saves ~60MB)
- `numpy` (saves ~53MB)
- `db-dtypes` (saves ~2MB)
- `google-cloud-bigquery` (saves ~30MB)

**Keep:**
- `httpx` (for API calls)
- `google-cloud-pubsub` (for job publishing)
- `fastapi`, `uvicorn`, `pydantic`

**Result:** ~200-250MB image (under CI limit!)

**Changes needed:**
```python
# ecommerce_base_connector.py
async def extract_data(...) -> AsyncGenerator[list[dict], None]:
    # Return raw JSON instead of DataFrame
    data = await self._get_products(...)
    yield data  # No pd.DataFrame conversion!
```

### Option 2: Heavy BigQuery API

**Keep:**
- All current dependencies
- Only BigQuery connector routes

**Result:** ~720MB image (for enterprise customers only)

---

## Why is Pandas Used in E-commerce Connectors?

Looking at [ecommerce_base_connector.py:232-269](services/data_ingestion_api/src/data_ingestion_api/connectors/ecommerce_base_connector.py:232-269):

```python
async def extract_data(
    self,
    resource: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    chunk_size: int = 100,
    client_id: str = ""
) -> AsyncGenerator[pd.DataFrame, None]:
    """
    Extrai dados da plataforma e retorna como DataFrame.  # ❌ WHY DATAFRAME?
    """
```

**Answer:** Because it inherits from `AbstractDataConnector` which forces this signature:

```python
# abstract_connector.py:39
@abstractmethod
async def extract_data(...) -> AsyncGenerator[pd.DataFrame, None]:
    """
    Retorna DataFrame de Pandas.  # ❌ WRONG ABSTRACTION!
    """
```

**The Problem:** The abstract class assumes ALL connectors need pandas DataFrames, but:
- **E-commerce connectors:** Return JSON (list of dicts) → forced to convert to DataFrame
- **BigQuery connector:** Returns tabular data → makes sense as DataFrame

---

## Recommended Changes

### 1. Fix the Abstract Connector

```python
# abstract_connector.py
from typing import Any, AsyncGenerator

@abstractmethod
async def extract_data(...) -> AsyncGenerator[Any, None]:
    """
    Returns data in the connector's native format:
    - E-commerce: list[dict] (JSON)
    - BigQuery: pd.DataFrame (tabular)
    """
```

### 2. Update E-commerce Connectors

```python
# ecommerce_base_connector.py
async def extract_data(...) -> AsyncGenerator[list[dict], None]:
    """Returns raw JSON data (no pandas conversion)."""
    data = await self._get_products(...)
    yield data  # No DataFrame!
```

### 3. Remove Pandas from E-commerce Dependencies

```toml
# pyproject.toml (ecommerce-only version)
[tool.poetry.dependencies]
fastapi = "^0.111.0"
httpx = "^0.27.0"
google-cloud-pubsub = "^2.21.0"
# NO pandas, pyarrow, numpy, bigquery!
```

**Result:** Image drops from 724MB to ~250MB ✅

---

## Why is the Current Image 724MB?

| Dependency | Size | Used By | Actually Needed? |
|-----------|------|---------|------------------|
| pyarrow | 60MB | BigQuery results | ❌ No (for e-commerce) |
| pandas | 47MB | All connectors | ❌ No (for e-commerce) |
| numpy | 53MB | pandas dependency | ❌ No (for e-commerce) |
| google-cloud-bigquery | 30MB | BigQuery connector | ❌ No (for e-commerce) |
| google-cloud-pubsub | 25MB | Job publishing | ✅ Yes (all connectors) |
| grpc | 15MB | Google Cloud | ❌ No (for e-commerce) |
| **TOTAL WASTE** | **~205MB** | | Can be removed! |

---

## Comparison: E-commerce API vs Analytics API

### Why is analytics_api lighter (92MB)?

**analytics_api does:**
- Database queries
- Simple aggregations
- No pandas/pyarrow
- Minimal dependencies

**data_ingestion_api does:**
- HTTP calls to e-commerce APIs (lightweight)
- BigQuery queries (heavyweight)
- Mixed in same service!

---

## Final Recommendation

### Immediate Action (No Code Split)

**Remove pandas from e-commerce connectors:**

1. Change return type from `pd.DataFrame` to `list[dict]`
2. Remove pandas dependency
3. Update abstract connector interface

**Result:** ~250MB image for e-commerce-only deployments

### Long-term Action (Service Split)

**Create two services:**
```
services/
├── ecommerce_ingestion_api/      # 200-250MB (Shopify, VTEX, etc.)
└── bigquery_ingestion_api/        # 700-750MB (Enterprise only)
```

**Benefits:**
- E-commerce API: Under CI limit (500MB)
- BigQuery API: Separate deployment for enterprise customers
- Clearer separation of concerns
- Easier to scale independently

---

## Questions to Answer

1. **What percentage of clients use BigQuery vs E-commerce connectors?**
   - If most use e-commerce → split makes sense
   - If most use BigQuery → keep as is

2. **Can we change the abstract connector interface?**
   - Will it break the worker?
   - Does the worker expect DataFrames or JSON?

3. **Is pandas actually used for transformations?**
   - Or is it just a pass-through format?
   - Can we remove it without breaking functionality?

---

**Next Steps:**
1. Check what format the worker expects
2. Run tests without pandas on e-commerce connectors
3. Decide: Split services OR just remove pandas from e-commerce path
