# Vizu Analytics API

> [!WARNING]
> **DEPRECATED** - This service is deprecated as of February 2026.
> All analytics queries have been migrated to Supabase PostgREST + RLS.
> The dashboard now queries `analytics_v2` schema views directly via Supabase client.
> See `apps/vizu_dashboard/src/services/analyticsService.ts` for the new implementation.
> This service remains for reference only and will be removed in a future release.

This service provides an API for data analytics in the Vizu application.

## Overview

The Vizu Analytics API is a FastAPI application that exposes endpoints for querying and analyzing data. It is responsible for transforming data from a "Silver" layer to a "Gold" layer, making it ready for consumption by the frontend or other services.

### Key Technologies

*   **Framework:** FastAPI
*   **Data Manipulation:** Pandas
*   **Database:** PostgreSQL (via `vizu_db_connector`)
*   **Package Manager:** Poetry
