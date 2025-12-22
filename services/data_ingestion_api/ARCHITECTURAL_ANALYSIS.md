# Data Ingestion Architecture - Critical Analysis

## The Real Problem: Circular Dependency & Code Duplication

### Current Architecture (BROKEN)

```
┌─────────────────────────────────────────────────────────────┐
│                    data_ingestion_api                         │
│  - Has ALL connectors (BigQuery, Shopify, VTEX, etc.)       │
│  - Has pandas/pyarrow dependencies (724MB)                   │
│  - Publishes jobs to Pub/Sub                                │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   │ pub/sub message
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              data_ingestion_worker (Cloud Function)          │
│  - IMPORTS ENTIRE data_ingestion_api! (line 23)             │
│  - Uses connectors from API                                  │
│  - DUPLICATES all dependencies (724MB + 724MB!)             │
└──────────────────────────────────────────────────────────────┘
```

**From worker's pyproject.toml:23**
```toml
data-ingestion-api = {path = "../data_ingestion_api", develop = true}
```

**From worker_function.py:10**
```python
from data_ingestion_api.connectors.bigquery_connector import BigQueryConnector
```

**From connector_factory.py:13-20**
```python
from data_ingestion_api.connectors import (
    LojaIntegradaConnector,
    ShopifyConnector,
    VTEXConnector,
)
from data_ingestion_api.connectors.bigquery_connector import BigQueryConnector
```

### The Problems

#### 1. **Code Duplication**
Both API and Worker have:
- Same connectors code
- Same pandas/pyarrow dependencies
- Same BigQuery SDK
- Same e-commerce HTTP logic

**Result:** 2x the deployment size, 2x the maintenance, 2x the bugs

#### 2. **Circular Responsibility**

**data_ingestion_api responsibilities:**
1. ✅ Receive credentials
2. ✅ Validate connections (test endpoints)
3. ✅ Publish jobs to Pub/Sub
4. ❌ **HAS ALL CONNECTOR CODE** (shouldn't be here!)
5. ❌ **HAS DATA EXTRACTION LOGIC** (should be in worker!)

**data_ingestion_worker responsibilities:**
1. ✅ Listen to Pub/Sub
2. ✅ Extract data (using connectors)
3. ✅ Transform data (schema mapping)
4. ✅ Load to Supabase
5. ❌ **IMPORTS ENTIRE API** (circular dependency!)

#### 3. **Inefficient Data Flow**

**Current flow:**
```
API receives request
  → API validates connection (uses connector code)
  → API publishes job to Pub/Sub
  → Worker receives job
  → Worker imports API connectors (duplicate code!)
  → Worker extracts data
  → Worker writes to Supabase
```

**What's actually used:**
- **API endpoints:** Only for validation and job publishing
- **Worker:** Does ALL the actual work

#### 4. **pandas is Required by Worker, Not API**

**Worker (ingestion_service.py:68-76):**
```python
async for chunk_df in self.connector.extract_data(query):
    # Transform using pandas
    transformed_df = chunk_df.rename(columns=mapping)
    # Load to DB
    await self.writer.load(transformed_df)
```

**API endpoints:** Just validates connections and publishes jobs - **doesn't need pandas!**

---

## The Solution: Extract Connectors to Shared Library

### Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              libs/vizu_data_connectors (NEW!)                │
│  - BigQueryConnector                                         │
│  - ShopifyConnector, VTEXConnector, LojaIntegradaConnector  │
│  - Has pandas/pyarrow (only when needed)                     │
│  - Reusable by both API and Worker                          │
└──────────────┬────────────────────────────────┬─────────────┘
               │                                 │
               ▼                                 ▼
┌──────────────────────────────┐  ┌─────────────────────────────┐
│    data_ingestion_api        │  │  data_ingestion_worker      │
│  - Credential management     │  │  - Extract (uses lib)       │
│  - Connection validation     │  │  - Transform (pandas)       │
│  - Job publishing (Pub/Sub)  │  │  - Load (Supabase)          │
│  - NO data extraction!       │  │  - Has pandas/pyarrow       │
│  - LIGHTWEIGHT (~150MB)      │  │  (~400MB - acceptable)      │
└──────────────────────────────┘  └─────────────────────────────┘
```

### Benefits

1. **Single Source of Truth**
   - Connectors defined once in `libs/vizu_data_connectors`
   - Both API and Worker use the same code
   - Fix bugs once, benefits everywhere

2. **Lightweight API**
   - API only validates and publishes jobs
   - No pandas/BigQuery SDK needed
   - Image drops from 724MB to ~150MB ✅

3. **Heavy Worker (Where It Belongs)**
   - Worker does all the heavy lifting
   - Uses pandas for transformation
   - 400-500MB is acceptable for a worker

4. **No Circular Dependency**
   - API doesn't depend on Worker
   - Worker doesn't depend on API
   - Both depend on shared library

---

## Detailed Refactoring Plan

### Step 1: Create `libs/vizu_data_connectors`

```
libs/vizu_data_connectors/
├── src/vizu_data_connectors/
│   ├── __init__.py
│   ├── base/
│   │   ├── abstract_connector.py
│   │   └── ecommerce_base_connector.py
│   ├── bigquery/
│   │   └── bigquery_connector.py
│   ├── ecommerce/
│   │   ├── shopify_connector.py
│   │   ├── vtex_connector.py
│   │   └── loja_integrada_connector.py
│   └── factory.py
├── pyproject.toml
└── README.md
```

**pyproject.toml:**
```toml
[tool.poetry.dependencies]
python = "^3.11"
httpx = "^0.27.0"  # For e-commerce
pandas = "^2.2.0"   # For data transformation
google-cloud-bigquery = "^3.21.0"  # Optional, only if BigQuery used
```

### Step 2: Update data_ingestion_api

**Remove:**
- `src/data_ingestion_api/connectors/` (move to lib)
- pandas, pyarrow, numpy, db-dtypes
- google-cloud-bigquery (only if validation can be done differently)

**Keep:**
- google-cloud-pubsub (for job publishing)
- httpx (for connection validation)
- FastAPI endpoints

**Add dependency:**
```toml
[tool.poetry.dependencies]
vizu-data-connectors = {path = "../../libs/vizu_data_connectors", develop = true, extras = ["ecommerce"]}
# No BigQuery extra needed!
```

**New size:** ~150-200MB ✅

### Step 3: Update data_ingestion_worker

**Remove:**
- Dependency on `data-ingestion-api`

**Add dependency:**
```toml
[tool.poetry.dependencies]
vizu-data-connectors = {path = "../../libs/vizu_data_connectors", develop = true, extras = ["bigquery", "ecommerce"]}
pandas = "^2.2.0"  # For transformations
```

**Update imports:**
```python
# OLD
from data_ingestion_api.connectors.bigquery_connector import BigQueryConnector

# NEW
from vizu_data_connectors.bigquery import BigQueryConnector
```

---

## Responsibility Matrix (After Refactor)

| Responsibility | API | Worker | Shared Lib |
|---------------|-----|--------|-----------|
| Credential storage | ✅ | | |
| Connection validation | ✅ | | ✅ (uses connector) |
| Job publishing | ✅ | | |
| Data extraction | | ✅ | ✅ (connector code) |
| Data transformation | | ✅ | |
| Data loading | | ✅ | |
| Connector implementations | | | ✅ |

---

## Migration Path

### Phase 1: Create Shared Library (Week 1)
1. Create `libs/vizu_data_connectors`
2. Copy connector code from API
3. Add tests
4. Publish to local monorepo

### Phase 2: Update Worker (Week 2)
1. Add dependency on `vizu-data-connectors`
2. Update imports
3. Test all connector types
4. Deploy worker

### Phase 3: Update API (Week 3)
1. Remove connector code
2. Remove heavy dependencies
3. Update validation logic (use lib)
4. Deploy API (now ~150MB!)

### Phase 4: Cleanup
1. Remove old connector code from API
2. Update documentation
3. Archive old Docker images

---

## Expected Results

### Before
| Service | Size | Dependencies |
|---------|------|--------------|
| data_ingestion_api | 724MB | pandas, bigquery, pubsub |
| data_ingestion_worker | 724MB | imports entire API |
| **TOTAL** | **1.4GB** | Duplicated |

### After
| Service | Size | Dependencies |
|---------|------|--------------|
| data_ingestion_api | ~150MB | pubsub only |
| data_ingestion_worker | ~400MB | lib + pandas |
| vizu_data_connectors | N/A (lib) | pandas, bigquery, httpx |
| **TOTAL** | **~550MB** | Shared |

**Savings:** ~850MB (60% reduction!)

---

## Answers to Your Questions

### "What does this service actually do?"
**API:** Validates credentials and publishes jobs
**Worker:** Extracts, transforms, loads data

### "Why is BigQuery heavy?"
Because it needs pandas/pyarrow for data transformation - but only the **WORKER** needs it!

### "Why is analytics_api lighter?"
Because it only queries PostgreSQL and returns JSON - no pandas, no BigQuery!

### "What inefficiencies exist?"
1. **Code duplication** (API and Worker have same connectors)
2. **Circular dependency** (Worker imports API)
3. **Wrong responsibilities** (API has extraction code it doesn't use)
4. **2x deployment size** (both services have same dependencies)

---

## Recommendation

**Don't optimize the current image - refactor the architecture:**

1. ✅ Extract connectors to `libs/vizu_data_connectors`
2. ✅ Make API lightweight (credentials + validation + pub/sub only)
3. ✅ Keep Worker heavy (it does the actual work)
4. ✅ Eliminate circular dependency

**Timeline:** 2-3 weeks
**Benefit:** 60% size reduction, cleaner architecture, easier maintenance

This is the **RIGHT** solution, not just an optimization!
