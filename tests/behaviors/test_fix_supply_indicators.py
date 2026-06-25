"""RED test — Fix Supply/Compras Indicators (ETL Loading) — Behavior 5/5."""
import re
from pathlib import Path
import pytest

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

ANALYTICS_TS_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "api" / "analytics.ts"
BASELINE_V2_PATH = REPO_ROOT / "supabase" / "migrations" / "20260523999999_baseline_v2.sql"
USE_ANALYTICS_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "hooks" / "useAnalytics.ts"
COMPRAS_ROOM_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "ComprasRoom.tsx"
BACKLOG_METRICAS_PATH = REPO_ROOT / "docs" / "backlog" / "05_frontend_e_metricas.md"

@pytest.fixture(autouse=True)
def _cleanup_test_data():
    yield

def _read_text(path):
    assert path.exists(), f"File not found: {path}"
    return path.read_text(encoding="utf-8")

def _baseline_sql():
    return _read_text(BASELINE_V2_PATH)

def _analytics_ts():
    return _read_text(ANALYTICS_TS_PATH)

def _use_analytics_ts():
    return _read_text(USE_ANALYTICS_PATH)

def _compras_room_ts():
    return _read_text(COMPRAS_ROOM_PATH)

def _backlog_metricas_md():
    return _read_text(BACKLOG_METRICAS_PATH)

def _extract_function_body(source, fn_name, start_marker="export const"):
    pattern = re.escape(start_marker) + r"\s+" + re.escape(fn_name) + r"\s*(?:<[^>]+>)?\s*=\s*async\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*=>\s*\{"
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        return ""
    body_start = match.end()
    depth, j, in_str, in_lc, in_bc = 1, body_start, None, False, False
    while j < len(source) and depth > 0:
        ch, nxt = source[j], source[j+1] if j+1 < len(source) else ""
        if in_lc:
            if ch == "\n": in_lc = False
            j += 1; continue
        if in_bc:
            if ch == "*" and nxt == "/": in_bc = False; j += 2; continue
            j += 1; continue
        if in_str is not None:
            if ch == "\\": j += 2; continue
            if ch == in_str: in_str = None; j += 1; continue
            j += 1; continue
        if ch == "/" and nxt == "/": in_lc = True; j += 2; continue
        if ch == "/" and nxt == "*": in_bc = True; j += 2; continue
        if ch in ('"', "'", "`"): in_str = ch; j += 1; continue
        if ch == "{": depth += 1
        elif ch == "}": depth -= 1
        j += 1
    if depth != 0: return ""
    return source[body_start:j-1]

def _extract_public_supply_indicators_body(sql):
    pattern = re.compile(r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.get_supply_indicators\s*\([^)]*\)[^$]*\$function\$", re.DOTALL | re.IGNORECASE)
    match = pattern.search(sql)
    if not match: return ""
    body_start = match.end()
    close = re.search(r"\$function\$\s*;", sql[body_start:], re.IGNORECASE)
    if not close: return ""
    return sql[body_start:body_start+close.start()]

def test_fix_supply_ac1_analytics_v2_rpc_must_exist():
    sql = _baseline_sql()
    pattern = re.compile(r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_supply_indicators\s*\([^)]*\)[^$]*\$function\$[^$]+\$function\$", re.DOTALL | re.IGNORECASE)
    assert pattern.search(sql), "AC1 RED: analytics_v2.get_supply_indicators not defined in baseline_v2.sql"

def test_fix_supply_ac2_get_supply_indicators_must_not_hang_on_loading():
    analytics_source = _analytics_ts()
    fn_body = _extract_function_body(analytics_source, "getSupplyIndicators")
    assert fn_body, "Cannot extract getSupplyIndicators body"
    api_protected = bool(re.search(r"\btry\s*\{", fn_body)) and bool(re.search(r"\bcatch\s*[({]", fn_body))
    hook_source = _use_analytics_ts()
    hook_protected = bool(re.search(r"useSupplyIndicators.*?\breTry\s*:\s*(?:false|0)\b", hook_source, re.DOTALL)) or bool(re.search(r"\b(?:LOADING_TIMEOUT_MS|loadingTimeout|loading_timeout)\b", hook_source)) or bool(re.search(r"\bsetTimeout\s*\(", hook_source))
    assert api_protected or hook_protected, "AC2 RED: no infinite-loading protection (try/catch or retry:false)"

def test_fix_supply_ac3_must_return_data_from_fato_transacoes():
    sql = _baseline_sql()
    av2_pat = re.compile(r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_supply_indicators\s*\([^)]*\)", re.DOTALL | re.IGNORECASE)
    av2_exists = av2_pat.search(sql) is not None
    if av2_exists:
        body_match = re.search(r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_supply_indicators\s*\([^)]*\)[^$]*\$function\$([^$]+)\$function\$", sql, re.DOTALL | re.IGNORECASE)
        body = re.sub(r"\s+", " ", body_match.group(1)) if body_match else ""
        refs_fato = bool(re.search(r"\bfato_transacoes\b", body, re.IGNORECASE))
        has_metrics = refs_fato and (bool(re.search(r"\blead_time\b", body, re.IGNORECASE)) or bool(re.search(r"\botif\b", body, re.IGNORECASE)) or bool(re.search(r"\bcost_savings\b", body, re.IGNORECASE)))
        assert has_metrics, "AC3 RED: analytics_v2 function exists but does not query fato_transacoes"
    else:
        body = _extract_public_supply_indicators_body(sql)
        body_n = re.sub(r"\s+", " ", body)
        assert bool(re.search(r"\bfato_transacoes\b", body_n, re.IGNORECASE)), f"AC3 RED: public.get_supply_indicators does not reference fato_transacoes. Body: {body_n[:120]}"

def test_fix_supply_ac4_must_have_fallback_zeros_with_period():
    sql = _baseline_sql()
    sql_body = re.sub(r"\s+", " ", _extract_public_supply_indicators_body(sql))
    sql_fb = bool(re.search(r"\bCOALESCE\s*\(|UNION\s+ALL\b|\bIS\s+NULL\b|\bCASE\s+WHEN\b|\bIFNULL\s*\(|\bNULLIF\s*\(", sql_body, re.IGNORECASE))
    fn_body = _extract_function_body(_analytics_ts(), "getSupplyIndicators")
    ts_fb = bool(re.search(r"\btry\s*\{", fn_body)) and bool(re.search(r"\bcatch\s*[({]", fn_body)) if fn_body else False
    assert sql_fb or ts_fb, "AC4 RED: no fallback (SQL COALESCE/UNION or TS try/catch)"

def test_fix_supply_ac5_lead_time_gap_documented_and_available_data_used():
    try: backlog_md = _backlog_metricas_md()
    except AssertionError: backlog_md = ""
    gap_doc = bool(re.search(r"promised_delivery_at", backlog_md, re.IGNORECASE)) if backlog_md else False
    sql = _baseline_sql()
    promised_in_schema = bool(re.search(r"\bpromised_delivery_at\b", sql, re.IGNORECASE))
    av2_match = re.search(r"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+analytics_v2\.get_supply_indicators\s*\([^)]*\)[^$]*\$function\$([^$]+)\$function\$", sql, re.DOTALL | re.IGNORECASE)
    if not promised_in_schema:
        if not gap_doc:
            pytest.fail("AC5 RED: promised_delivery_at gap not documented")
        if av2_match:
            body_n = re.sub(r"\s+", " ", av2_match.group(1))
            has_lt = bool(re.search(r"\blead_time\b", body_n, re.IGNORECASE))
            has_dc = bool(re.search(r"\bdata_criacao\b", body_n, re.IGNORECASE))
            has_da = bool(re.search(r"\bdata_aprovacao\b", body_n, re.IGNORECASE))
            if has_lt and (has_dc or has_da): return
        pytest.fail("AC5 RED: analytics_v2 function does not use available data for lead_time")
    else:
        pytest.skip("promised_delivery_at exists, AC5 not applicable")
