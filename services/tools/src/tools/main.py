from typing import List, Optional

from fastapi import FastAPI, Query

from tools.monitoring_service import WebMonitorService, get_monitor_instance

app = FastAPI(title="Vizu Tools Service")


@app.get("/monitor-feature")
async def monitor_feature(domain: str, query: str):
    monitor = await get_monitor_instance(domain)
    result = await monitor.monitor_feature(query)
    return {"results": result}


@app.get("/monitor-keywords")
async def monitor_keywords(domain: str, keywords: list[str] = Query(...)):
    monitor = await get_monitor_instance(domain)
    result = await monitor.monitor_keywords(keywords)
    return {"results": result}


@app.get("/monitor-company")
async def monitor_company(company: str, domains: list[str] | None = Query(None)):
    use_domain = domains[0] if domains and len(domains) > 0 else "zerezes.com.br"
    monitor = await get_monitor_instance(use_domain)
    result = await monitor.monitor_company_web(company, extra_domains=domains or [])
    return {"results": result}
