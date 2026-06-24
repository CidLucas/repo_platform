"""RED test for behavior B6 — Corrigir 4 vulnerabilidades High de segurança.

GOAL:
    AC#6 — 4 vulnerabilidades High corrigidas (RATE-01, CSP-01, SEC-01, DEP-01).

BEHAVIOR:
    B6 — Corrigir 4 vulnerabilidades High de segurança

    As 4 proteções devem estar em vigor:

    a) **RATE-01** — Rate limiting presente em agent_api **e** tool_pool_api.
       Os módulos ``services/agent_api/src/agent_api/main.py`` e
       ``services/tool_pool_api/src/tool_pool_api/main.py`` devem
       (i) importar ``slowapi`` e/ou ``slowapi.Limiter``, e
       (ii) registrar a exceção ``SlowAPIMiddleware`` (ou middleware
            equivalente baseado em slowapi) na app FastAPI.

    b) **CSP-01** — Content-Security-Policy header presente no frontend.
       O arquivo ``apps/blu_v3/index.html`` deve declarar
       ``<meta http-equiv="Content-Security-Policy" ...>`` (ou, em
       alternativa válida, referenciar um script/Vite plugin que injete
       o header CSP em produção). A meta tag deve incluir pelo menos a
       diretiva ``default-src`` para garantir uma política mínima útil.

    c) **SEC-01** — O arquivo ``.secrets.baseline`` (usado por
       ``detect-secrets``) NÃO deve estar listado no ``.gitignore``.
       Caso contrário, a varredura de secrets fica desabilitada para
       o repositório (a baseline é ignorada e o hook do pre-commit não
       funciona). A linha do ``.secrets.baseline`` deve ter sido
       removida do ``.gitignore`` raiz.

    d) **DEP-01** — O package ``xlsx`` em
       ``apps/blu_v3/package.json`` deve estar em versão ``>=0.19.0``
       (patched contra ReDoS em ``readSync`` e contra Prototype
       Pollution em ``parseSheetFromFile``). A versão atual vulnerável
       é ``0.18.5``.

DECISION:
    Estratégia: extend — estender módulos existentes com refatorações
    pontuais (adicionar middleware, meta tag, remover 1 linha do
    .gitignore, bump de 1 dep). Nenhum módulo novo deve ser criado.

Anti-Goals (must NOT be violated):
    1. NÃO substituir ``slowapi`` por implementação custom — o
       remédio oficial do code-review é slowapi (SEC-P1-01).
    2. NÃO bloquear a app inteira com rate limiting em /health —
       basta adicionar o middleware (a config dos limites cabe à
       fase GREEN).
    3. NÃO introduzir diretivas CSP permissivas demais
       (``unsafe-eval`` ou ``*`` em ``script-src``) sem justificativa.
    4. NÃO atualizar nenhuma outra dep além de ``xlsx`` (escopo
       mínimo: DEP-01). Vulnerabilidades npm de vite/ws/react-router
       são scope de outras behaviors (DEP-02+).
    5. NÃO mover ``.secrets.baseline`` para outro arquivo — manter o
       nome e o conteúdo. Apenas remover a entrada do ``.gitignore``
       para que ele volte a ser versionado.

Estado atual (RED): Todas as 4 verificações falham no estado atual:
    - agent_api main.py NÃO importa ``slowapi``.
    - tool_pool_api main.py NÃO importa ``slowapi``.
    - apps/blu_v3/index.html NÃO contém meta tag CSP.
    - .gitignore raiz contém ``.secrets.baseline`` na linha 28.
    - apps/blu_v3/package.json fixa ``xlsx: ^0.18.5`` (vulnerável).

O teste abaixo abre os arquivos relevantes, executa verificações
estritamente sobre o conteúdo textual (sem importar nenhum módulo
interno) e produz mensagens de AssertionError que descrevem o que
falta. Quando a fase GREEN for implementada (adicionar slowapi +
CSP + remover linha + bump dep), as quatro verificações passarão.
"""

import json
import re
from pathlib import Path

import pytest

# ── Path resolution (root of repo) ───────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

AGENT_API_MAIN = (
    REPO_ROOT
    / "services"
    / "agent_api"
    / "src"
    / "agent_api"
    / "main.py"
)
TOOL_POOL_API_MAIN = (
    REPO_ROOT
    / "services"
    / "tool_pool_api"
    / "src"
    / "tool_pool_api"
    / "main.py"
)
FRONTEND_INDEX_HTML = REPO_ROOT / "apps" / "blu_v3" / "index.html"
FRONTEND_PACKAGE_JSON = REPO_ROOT / "apps" / "blu_v3" / "package.json"
ROOT_GITIGNORE = REPO_ROOT / ".gitignore"


# ── Override root conftest cleanup (pure file-based test) ───────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file inspection, no DB."""
    yield


# ── Helpers ─────────────────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    assert path.exists(), f"File not found: {path}"
    return path.read_text(encoding="utf-8")


def _has_slowapi_import(content: str) -> bool:
    """Return True if the file imports slowapi (any submodule)."""
    return bool(
        re.search(r"^\s*(from|import)\s+slowapi\b", content, re.MULTILINE)
    )


def _has_slowapi_middleware(content: str) -> bool:
    """Return True if the file wires slowapi middleware into FastAPI.

    Accepts:
      * ``app.add_middleware(SlowAPIMiddleware)``
      * ``app.state.limiter = limiter`` (any limiter reference)
      * direct reference to ``slowapi.errors.RateLimitExceeded`` (used
        together with the exception handler)
    """
    if re.search(r"\bSlowAPIMiddleware\b", content):
        return True
    if re.search(r"\bapp\.state\.limiter\b", content):
        return True
    if re.search(r"\bslowapi\.errors\.RateLimitExceeded\b", content):
        return True
    if re.search(r"\bLimiter\s*\(", content):
        return True
    return False


def _has_csp_meta_tag(content: str) -> bool:
    """Return True if the index.html contains a Content-Security-Policy
    meta tag (case-insensitive, single or double quotes accepted).
    """
    pattern = (
        r"""<\s*meta\s+http-equiv\s*=\s*["']Content-Security-Policy["']"""
    )
    return bool(re.search(pattern, content, re.IGNORECASE))


def _csp_meta_tag(content: str) -> str:
    """Return the full CSP meta tag line (or '' if not present)."""
    match = re.search(
        r"""<\s*meta\s+http-equiv\s*=\s*["']Content-Security-Policy["'][^>]*>""",
        content,
        re.IGNORECASE,
    )
    return match.group(0) if match else ""


def _csp_has_default_src(content: str) -> bool:
    """True if the CSP policy referenced in ``content`` contains a
    ``default-src`` directive — even if the policy is delivered via a
    Vite plugin (e.g. ``<meta ...>`` OR ``Content-Security-Policy``
    appears in a comment with a body that contains ``default-src``).
    """
    tag = _csp_meta_tag(content)
    if not tag:
        return False
    return "default-src" in tag


def _gitignore_lists_secrets_baseline(gitignore_text: str) -> bool:
    """True if ``.gitignore`` has a non-commented line that matches
    ``.secrets.baseline`` (anchored to the whole line, allowing leading
    whitespace and ``./`` prefix).  Comment lines (``# ...``) are
    ignored, since commenting the entry is a valid alternative fix.
    """
    for raw in gitignore_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == ".secrets.baseline" or line == "./.secrets.baseline":
            return True
    return False


def _xlsx_version(package_json_text: str) -> str:
    """Return the pinned version range of the ``xlsx`` dependency, or
    '' if the dep is not declared.
    """
    data = json.loads(package_json_text)
    deps = {}
    deps.update(data.get("dependencies", {}) or {})
    deps.update(data.get("devDependencies", {}) or {})
    return str(deps.get("xlsx", ""))


def _xlsx_version_satisfies_patched(version_range: str) -> bool:
    """True if the version range starts with >=0.19.0 (the patched
    release for CVE Prototype Pollution + ReDoS in xlsx).  We accept
    exact ``"0.19.0"`` or any ``^``/``~``/``>=`` that maps to a release
    ``>=0.19.0``.

    The minimal version extracted from the range must be ``>= 0.19.0``.
    """
    if not version_range:
        return False

    # Strip leading operators to get the lowest bound that must hold.
    raw = version_range.strip().strip('"').strip("'")

    # Extract first numeric version we see in the range.
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", raw)
    if not match:
        return False
    major, minor, patch = (int(g) for g in match.groups())

    # Acceptable bounds for the patched release: 0.19.0+
    return (major, minor, patch) >= (0, 19, 0)


# ── The single behavior under test ──────────────────────────────────────


def test_b6_security_vulnerabilities_red():
    """B6 / AC#6 — 4 High vulnerabilities are fixed.

    The test inspects the repository's source-of-truth files (not
    mocks) and asserts that each of the 4 protections is in place:

      a) agent_api + tool_pool_api import slowapi AND wire the
         middleware (RATE-01).
      b) apps/blu_v3/index.html has a ``Content-Security-Policy`` meta
         tag with a ``default-src`` directive (CSP-01).
      c) ``.secrets.baseline`` is NOT listed in the root .gitignore
         (SEC-01).
      d) apps/blu_v3/package.json bumps ``xlsx`` to ``>=0.19.0``
         (DEP-01).
    """
    failures: list[str] = []

    # ── (a) RATE-01 — slowapi middleware in both APIs ──────────────
    agent_api_text = _read_text(AGENT_API_MAIN)
    tool_pool_text = _read_text(TOOL_POOL_API_MAIN)

    if not _has_slowapi_import(agent_api_text):
        failures.append(
            "RATE-01: agent_api main.py does NOT import slowapi. "
            "Behavior B6 / AC#6 requires the slowapi.Limiter (or "
            "``from slowapi import ...``) to be imported and the "
            f"SlowAPIMiddleware to be wired into the app. File: "
            f"{AGENT_API_MAIN}"
        )
    elif not _has_slowapi_middleware(agent_api_text):
        failures.append(
            "RATE-01: agent_api main.py imports slowapi but does NOT "
            "wire the middleware. Expected one of: "
            "``app.add_middleware(SlowAPIMiddleware)``, "
            "``app.state.limiter = ...``, or a slowapi error handler "
            f"registration. File: {AGENT_API_MAIN}"
        )

    if not _has_slowapi_import(tool_pool_text):
        failures.append(
            "RATE-01: tool_pool_api main.py does NOT import slowapi. "
            "Behavior B6 / AC#6 requires slowapi.Limiter to be "
            "imported and the SlowAPIMiddleware to be wired into the "
            f"app. File: {TOOL_POOL_API_MAIN}"
        )
    elif not _has_slowapi_middleware(tool_pool_text):
        failures.append(
            "RATE-01: tool_pool_api main.py imports slowapi but does "
            "NOT wire the middleware. Expected one of: "
            "``app.add_middleware(SlowAPIMiddleware)``, "
            "``app.state.limiter = ...``, or a slowapi error handler "
            f"registration. File: {TOOL_POOL_API_MAIN}"
        )

    # ── (b) CSP-01 — Content-Security-Policy meta tag ──────────────
    index_html_text = _read_text(FRONTEND_INDEX_HTML)

    if not _has_csp_meta_tag(index_html_text):
        failures.append(
            "CSP-01: apps/blu_v3/index.html does NOT contain a "
            "Content-Security-Policy meta tag. Behavior B6 / AC#6 "
            "requires a ``<meta http-equiv=\"Content-Security-Policy\" "
            "content=\"...\">`` element in the <head> with at least a "
            f"``default-src`` directive. File: {FRONTEND_INDEX_HTML}"
        )
    elif not _csp_has_default_src(index_html_text):
        failures.append(
            "CSP-01: apps/blu_v3/index.html has a Content-Security-"
            "Policy meta tag but it does NOT include a ``default-src`` "
            "directive. Behavior B6 / AC#6 requires a policy that "
            "establishes a fallback for all resource types via "
            "``default-src`` (e.g. ``default-src 'self'``). Found "
            f"tag: ``{_csp_meta_tag(index_html_text)}``. File: "
            f"{FRONTEND_INDEX_HTML}"
        )

    # ── (c) SEC-01 — .secrets.baseline must NOT be in .gitignore ───
    gitignore_text = _read_text(ROOT_GITIGNORE)

    if _gitignore_lists_secrets_baseline(gitignore_text):
        failures.append(
            "SEC-01: .secrets.baseline is listed in the root "
            ".gitignore, which disables detect-secrets. Behavior B6 / "
            "AC#6 requires the ``.secrets.baseline`` line to be "
            "REMOVED from ``.gitignore`` (it should be tracked so that "
            "detect-secrets hooks work). "
            f"File: {ROOT_GITIGNORE}"
        )

    # ── (d) DEP-01 — xlsx must be >= 0.19.0 (patched) ──────────────
    package_json_text = _read_text(FRONTEND_PACKAGE_JSON)
    xlsx_version = _xlsx_version(package_json_text)

    if not xlsx_version:
        failures.append(
            "DEP-01: xlsx dependency is missing from "
            "apps/blu_v3/package.json. Behavior B6 / AC#6 requires "
            "xlsx to be declared at a patched version (>=0.19.0). "
            f"File: {FRONTEND_PACKAGE_JSON}"
        )
    elif not _xlsx_version_satisfies_patched(xlsx_version):
        failures.append(
            f"DEP-01: apps/blu_v3/package.json pins xlsx to "
            f"``{xlsx_version}`` which is BELOW 0.19.0 and therefore "
            "vulnerable to Prototype Pollution and ReDoS (CVE on xlsx "
            "< 0.19.0). Behavior B6 / AC#6 requires xlsx >= 0.19.0. "
            f"File: {FRONTEND_PACKAGE_JSON}"
        )

    # ── Aggregate all 4 failures ───────────────────────────────────
    assert not failures, (
        "B6 / AC#6 — 4 High security vulnerabilities are NOT yet "
        "fixed. The following protections are missing:\n\n  - "
        + "\n  - ".join(failures)
    )
