"""RED test for onboarding-website-intel extraction (CNPJ, phone, verticals, edge cases).

GOAL:
    Expandir a edge function ``supabase/functions/onboarding-website-intel/index.ts``
    com:

        - ``extractCNPJ()`` que extrai CNPJ de texto puro, de tags ``<meta>``
          e de blocos ``<script type="application/ld+json">`` (JSON-LD).
        - ``validateCNPJ()`` que valida CNPJ via dígitos verificadores
          (algoritmo mod-11 padrão CNPJ).
        - ``extractPhone()`` que extrai telefones BR (10-11 dígitos).
        - 5 novas verticais detectáveis: ``design``, ``buffet``,
          ``construcao``, ``logistica``, ``consultoria``.
        - Confidence scoring dinâmico baseado no número de fontes
          (1=0.3, 2=0.5, 3+=0.7).
        - Timeout de 10.000ms no ``fetch`` interno.
        - Resposta inclui ``cnpj``, ``telefone`` e ``confidence_details``
          tanto no caminho feliz quanto no caminho de URL vazia e no
          fallback de SPA / erro.
        - Try/catch em torno do ``fetch`` que retorna um fallback
          gracioso (cnpj=null, telefone=null, confidence=0 etc.) quando
          o site é uma SPA sem HTML server-rendered.

BEHAVIOR:
    B8.1 — Extração estruturada (CNPJ, telefone) e novos sinais de
    detecção para a edge function ``onboarding-website-intel``.

AC (Acceptance Criteria):
    AC#1  — ``extractCNPJ()`` extrai CNPJ de texto HTML livre
            (formato ``\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}``).
    AC#2  — ``extractCNPJ()`` extrai CNPJ de tags ``<meta>`` (ex:
            ``<meta property="article:author" content="00.000.000/0001-00">``).
    AC#3  — ``extractCNPJ()`` extrai CNPJ de JSON-LD (ex:
            ``"vatID": "00.000.000/0001-00"``).
    AC#4  — ``validateCNPJ()`` valida dígitos verificadores via mod-11.
            Aceita CNPJs válidos conhecidos e rejeita inválidos
            (canary via subprocess Node).
    AC#5  — ``extractPhone()`` extrai telefones BR (10-11 dígitos) com
            e sem pontuação.
    AC#6  — ``detectVertical()`` detecta 5 novas verticais: design,
            buffet, construcao, logistica, consultoria.
    AC#7  — Confidence scoring dinâmico: 1=0.3, 2=0.5, 3+=0.7.
    AC#8  — Timeout do ``fetch`` interno é 10.000ms.
    AC#9  — URL vazia (após ``normalizeUrl``) retorna ``confidence: 0``
            e a resposta inclui os novos campos ``cnpj``,
            ``telefone`` e ``confidence_details``.
    AC#10 — ``fetch`` que retorna HTML vazio / erro de rede é tratado
            por um try/catch e cai em um fallback gracioso que inclui
            ``cnpj``, ``telefone`` e ``confidence_details`` (não há
            500/crash).

DECISION:
    Estratégia: extend — editar
    ``supabase/functions/onboarding-website-intel/index.ts`` in-place.
    Nenhum arquivo novo deve ser criado. As funções novas
    (``extractCNPJ``, ``extractPhone``, ``validateCNPJ``) são adicionadas
    ao mesmo arquivo. ``detectVertical`` é estendido com as 5 novas
    keywords.

Anti-Goals (must NOT be violated):
    1. NÃO substituir ``stripHtml`` / ``normalizeUrl`` (utilitários
       corretos).
    2. NÃO alterar a assinatura pública de ``Deno.serve``.
    3. NÃO remover ``suggestFromVertical``.
    4. NÃO importar bibliotecas externas de validação de CNPJ — a
       implementação deve ser local ao arquivo, sem novas deps.
    5. NÃO criar arquivos auxiliares em ``supabase/functions/_shared``
       para esta expansão.

Test strategy:
    Source inspection (lê o ``.ts`` como texto) porque ``Deno.serve()``
    inicia um listener de rede real quando executado, o que tornaria o
    teste flaky e dependente de runtime Deno. As funções puras
    (``detectVertical``, ``extractCNPJ``, ``extractPhone``,
    ``validateCNPJ``) são validadas via regex e/ou via extração +
    ``new Function(...)`` quando possível. Para ``validateCNPJ`` o teste
    inclui uma canary-suite: executa a função extraída do source
    (sem rede, sem Deno) em subprocess Node e verifica que aceita
    CNPJs válidos conhecidos e rejeita inválidos.

Estado atual (RED):
    - ``extractCNPJ`` NÃO está definida.
    - ``extractPhone`` NÃO está definida.
    - ``validateCNPJ`` NÃO está definida.
    - ``detectVertical`` NÃO contém as 5 novas keywords (design, buffet,
      construcao, logistica, consultoria).
    - Timeout do ``fetch`` é 5000ms (deveria ser 10000ms).
    - Confidence hard-coded em ``vertical ? 0.72 : 0.45``.
    - Resposta NÃO inclui ``cnpj``, ``telefone`` nem
      ``confidence_details``.
"""

from __future__ import annotations

import json as _json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

# ── Path resolution (repo root) ──────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

INDEX_TS_PATH = (
    REPO_ROOT
    / "supabase"
    / "functions"
    / "onboarding-website-intel"
    / "index.ts"
)

# 5 novas verticais exigidas por AC#6.
NEW_VERTICAL_KEYWORDS: tuple[str, ...] = (
    "design",
    "buffet",
    "construcao",
    "logistica",
    "consultoria",
)

# Padrão de CNPJ formatado (BR): 00.000.000/0000-00.
# Usado em várias ACs como "ground truth" do regex.
CNPJ_FORMATTED_REGEX = r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"


# ── Override root conftest cleanup (pure file-based test) ────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file inspection, no DB."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────────


def _read_index_ts() -> str:
    """Read the full ``index.ts`` source as text."""
    assert INDEX_TS_PATH.exists(), (
        f"index.ts not found at {INDEX_TS_PATH}"
    )
    return INDEX_TS_PATH.read_text(encoding="utf-8")


def _extract_function_body(source: str, fn_name: str) -> str:
    """Extract the body of a top-level function declaration.

    Looks for ``function <fn_name>(`` and returns the text from the
    function declaration up to the matching closing brace.
    """
    marker = f"function {fn_name}("
    idx = source.find(marker)
    assert idx != -1, (
        f"Could not find '{marker}' in {INDEX_TS_PATH}"
    )

    brace_start = source.find("{", idx)
    assert brace_start != -1, (
        f"Could not find opening brace for {fn_name}"
    )

    depth = 0
    end = -1
    for i in range(brace_start, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    assert end != -1, (
        f"Could not find closing brace for {fn_name}"
    )
    return source[idx:end]


def _function_is_declared(source: str, fn_name: str) -> bool:
    """True if ``function <fn_name>`` is declared at top-level scope.

    Accepts declarations like:
        * ``function foo(...)``
        * ``async function foo(...)``
        * ``export function foo(...)``
    """
    pattern = (
        r"(?:^|\n)\s*(?:export\s+)?(?:async\s+)?function\s+"
        + re.escape(fn_name)
        + r"\s*\("
    )
    return bool(re.search(pattern, source))


def _detect_vertical_keyword(source: str, keyword: str) -> str | None:
    """Find which vertical ``detectVertical`` returns for a given keyword.

    Returns the vertical name (string after ``return "..."``) if the
    keyword is wired into ``detectVertical``; ``None`` otherwise.
    """
    body = _extract_function_body(source, "detectVertical")

    # Walk each ``if (/(...)/.test(t)) return "VERTICAL";`` branch in order.
    branch_pattern = re.compile(
        r"if\s*\(/\(([^)]+)\)/\.(?:test|exec|match)\([^)]+\)\)\s*return\s+\"([^\"]+)\""
    )
    for m in branch_pattern.finditer(body):
        regex_inner = m.group(1)
        vertical = m.group(2)
        if keyword in regex_inner:
            return vertical
    return None


def _extract_fetch_block(source: str) -> str:
    """Extract the ``try { ... } catch { ... }`` block that wraps the fetch.

    Returns the text of the inner try block (or the whole try/catch
    block if the inner is not findable). Used to verify AC#10.
    """
    marker = "await fetch("
    idx = source.find(marker)
    assert idx != -1, (
        f"Could not find 'await fetch(' in {INDEX_TS_PATH}"
    )

    # Walk backwards from the fetch to the enclosing ``try {``.
    try_idx = source.rfind("try", 0, idx)
    assert try_idx != -1, (
        f"Could not find 'try' block enclosing fetch in {INDEX_TS_PATH}"
    )

    brace_start = source.find("{", try_idx)
    assert brace_start != -1, (
        "Could not find opening brace of try block"
    )

    depth = 0
    end = -1
    for i in range(brace_start, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    assert end != -1, "Could not find closing brace of try block"
    return source[try_idx:end]


# ── Tests ────────────────────────────────────────────────────────────────────


def test_extract_source_file_exists():
    """Sanity check: the source file must exist and import shared CORS."""
    assert INDEX_TS_PATH.exists(), (
        f"Source file not found: {INDEX_TS_PATH}"
    )
    source = _read_index_ts()
    assert "Deno.serve" in source, (
        "Deno.serve entrypoint not found in onboarding-website-intel/index.ts"
    )
    assert "corsHeaders" in source, (
        "corsHeaders import not found in onboarding-website-intel/index.ts"
    )


# ── AC#1 ─────────────────────────────────────────────────────────────────────


def test_ac1_extract_cnpj_from_raw_html_text():
    """AC#1 — ``extractCNPJ()`` extrai CNPJ de texto HTML livre.

    GOAL:
        A função ``extractCNPJ()`` deve existir e seu corpo deve
        conter um regex capaz de capturar o formato padrão de CNPJ
        (``\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}``) a partir de texto
        livre (sem delimitadores específicos de tag).

    BEHAVIOR:
        Dado um HTML com texto ``"CNPJ: 11.222.333/0001-81"``, a
        função deve retornar a string ``"11.222.333/0001-81"`` (ou
        o CNPJ sem pontuação, conforme a implementação).

    AC#1:
        - ``extractCNPJ`` está declarada como função top-level.
        - O corpo da função contém o padrão regex do CNPJ
          formatado (``\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}``).
    """
    source = _read_index_ts()
    assert _function_is_declared(source, "extractCNPJ"), (
        "RED — function `extractCNPJ` is NOT declared in "
        f"onboarding-website-intel/index.ts. AC#1 requires a function "
        "that extracts CNPJ from free text in HTML. "
        f"File: {INDEX_TS_PATH}"
    )

    body = _extract_function_body(source, "extractCNPJ")
    # The body must reference the canonical CNPJ format. We accept
    # both the dotted form and the digit-only form (12 base digits
    # + DV1 + DV2 = 14 digits), but the dotted form is the most
    # common in raw HTML text.
    has_cnpj_pattern = re.search(CNPJ_FORMATTED_REGEX, body) or re.search(
        r"\\d\{2\}\\d\{3\}\\d\{3\}\\d\{4\}\\d\{2\}", body
    )
    assert has_cnpj_pattern, (
        "RED — extractCNPJ is declared but does NOT contain a regex "
        "matching the canonical CNPJ format "
        "(``\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}``). AC#1 requires "
        "the function to extract CNPJs from free text in HTML. "
        f"File: {INDEX_TS_PATH}"
    )


# ── AC#2 ─────────────────────────────────────────────────────────────────────


def test_ac2_extract_cnpj_from_meta_tag():
    """AC#2 — ``extractCNPJ()`` extrai CNPJ de tags ``<meta>``.

    GOAL:
        A função ``extractCNPJ()`` deve lidar com HTML que contém
        tags ``<meta>`` com CNPJ em atributos ``content``.

    BEHAVIOR:
        Dado o HTML
        ``<meta property="article:author" content="00.000.000/0001-00">``,
        a função deve retornar ``"00.000.000/0001-00"``.

    AC#2:
        - A regex no corpo de ``extractCNPJ`` deve capturar o CNPJ
          dentro do atributo ``content`` de uma ``<meta>`` tag.
        - Como o HTML das metas é tipicamente tratado via
          ``stripHtml`` (que remove tags), o regex também pode ser
          aplicado ao texto puro depois do stripping. Aceita-se:
            (a) referência ao atributo ``content=`` no regex, ou
            (b) chamada explícita a ``stripHtml`` antes do match.
    """
    source = _read_index_ts()
    assert _function_is_declared(source, "extractCNPJ"), (
        "RED — function `extractCNPJ` is NOT declared. AC#2 requires "
        f"CNPJ extraction from <meta> tags. File: {INDEX_TS_PATH}"
    )

    body = _extract_function_body(source, "extractCNPJ")
    # Accept either a direct meta-content regex (looks for
    # ``content=`` or ``content\s*=``) or a ``stripHtml`` call
    # before the regex (because stripping removes the <meta>
    # wrapper, leaving only the CNPJ text).
    has_meta_handling = (
        re.search(r"content\s*=", body, re.IGNORECASE)
        or re.search(r"stripHtml", body)
        or re.search(r"meta", body, re.IGNORECASE)
    )
    assert has_meta_handling, (
        "RED — extractCNPJ does NOT handle <meta> tag patterns. "
        "AC#2 requires the function to extract CNPJ from meta tags "
        "such as "
        "``<meta property=\"article:author\" content=\"00.000.000/0001-00\">``. "
        "Expected either a ``content=`` regex or a ``stripHtml`` "
        "call that neutralizes the <meta> wrapper. "
        f"File: {INDEX_TS_PATH}"
    )


# ── AC#3 ─────────────────────────────────────────────────────────────────────


def test_ac3_extract_cnpj_from_json_ld():
    """AC#3 — ``extractCNPJ()`` extrai CNPJ de JSON-LD.

    GOAL:
        A função ``extractCNPJ()`` deve lidar com HTML que contém
        blocos ``<script type="application/ld+json">`` com CNPJ no
        campo ``vatID``.

    BEHAVIOR:
        Dado o HTML
        ``<script type="application/ld+json">{"vatID": "00.000.000/0001-00"}</script>``,
        a função deve retornar ``"00.000.000/0001-00"``.

    AC#3:
        - A regex no corpo de ``extractCNPJ`` deve capturar o CNPJ
          após o campo ``vatID``.
        - Aceita-se também a presença de uma regex que captura o
          CNPJ dentro de aspas duplas (típico de JSON strings) ou
          referência explícita a ``vatID``.
    """
    source = _read_index_ts()
    assert _function_is_declared(source, "extractCNPJ"), (
        "RED — function `extractCNPJ` is NOT declared. AC#3 requires "
        f"CNPJ extraction from JSON-LD. File: {INDEX_TS_PATH}"
    )

    body = _extract_function_body(source, "extractCNPJ")
    has_jsonld_handling = (
        "vatID" in body
        or re.search(r"ld\s*\+\s*json", body, re.IGNORECASE)
        or re.search(r"application/ld\+json", body, re.IGNORECASE)
        or re.search(r"\\?[\"']\\s*:\\s*\\?[\"']", body)  # JSON key/value pair
        or re.search(r"JSON\.parse", body)
    )
    assert has_jsonld_handling, (
        "RED — extractCNPJ does NOT handle JSON-LD patterns. AC#3 "
        "requires the function to extract CNPJ from JSON-LD blocks "
        "such as "
        "``{\"vatID\": \"00.000.000/0001-00\"}``. Expected either a "
        "reference to ``vatID``, a match for ``application/ld+json``, "
        "or a ``JSON.parse`` call to parse the JSON-LD blob. "
        f"File: {INDEX_TS_PATH}"
    )


# ── AC#4 ─────────────────────────────────────────────────────────────────────


def test_ac4_validate_cnpj_check_digits_via_canary():
    """AC#4 — ``validateCNPJ()`` valida dígitos verificadores (mod-11).

    GOAL:
        A função ``validateCNPJ()`` deve existir, implementar o
        algoritmo mod-11 padrão CNPJ e diferenciar CNPJs válidos
        de inválidos.

    BEHAVIOR:
        * Válido: 11.222.333/0001-81  → ``true``
        * Válido: 04.337.168/0001-48  → ``true``
        * Inválido: 11.222.333/0001-82 → ``false``  (DV1 errado)
        * Inválido: 00.000.000/0000-00 → ``false``  (todos zeros)

    AC#4:
        - ``validateCNPJ`` está declarada.
        - O corpo usa ``% 11`` (mod-11) e referencia ``dv1``/``dv2``.
        - Canary via Node.js: a função extraída do source aceita
          CNPJs válidos e rejeita inválidos.
    """
    source = _read_index_ts()
    assert _function_is_declared(source, "validateCNPJ"), (
        "RED — function `validateCNPJ` is NOT declared in "
        f"onboarding-website-intel/index.ts. AC#4 requires check-digit "
        "validation via mod-11. File: {INDEX_TS_PATH}"
    )

    body = _extract_function_body(source, "validateCNPJ")
    assert "% 11" in body or "%11" in body, (
        "RED — validateCNPJ is declared but does NOT implement the "
        "mod-11 check digit algorithm. AC#4 requires ``sum % 11`` "
        f"to compute DV1 and DV2. File: {INDEX_TS_PATH}"
    )
    assert "dv1" in body.lower() and "dv2" in body.lower(), (
        "RED — validateCNPJ must compute both DV1 and DV2 (the two "
        "check digits of a CNPJ). Expected variables named ``dv1`` "
        f"and ``dv2`` in the function body. File: {INDEX_TS_PATH}"
    )

    # ── Canary: execute the function in a Node subprocess ──────────────
    arrow_body = re.sub(
        r"^function\s+validateCNPJ\s*\(([^)]*)\)\s*\{",
        r"globalThis.__validateCNPJ = function(\1) {",
        body,
        count=1,
    )
    js_source = arrow_body + "\n;"

    node = shutil.which("node")
    if node is None:
        pytest.skip(
            "node runtime not available; cannot execute the "
            "validateCNPJ canary for AC#4."
        )

    valid_cnpjs = (
        "11222333000181",
        "04337168000148",
        "11444777000161",
    )
    invalid_cnpjs = (
        "11222333000182",
        "00000000000000",
        "11111111111111",
        "12345678901234",
    )
    valid_literal = _json.dumps(valid_cnpjs)
    invalid_literal = _json.dumps(invalid_cnpjs)

    runner = (
        "const SOURCE = process.argv[1];\n"
        "const VALID = JSON.parse(process.argv[2]);\n"
        "const INVALID = JSON.parse(process.argv[3]);\n"
        "try {\n"
        "  new Function(SOURCE)();\n"
        "  if (typeof globalThis.__validateCNPJ !== 'function') {\n"
        "    process.stdout.write(JSON.stringify({ok: false, error: 'validateCNPJ not assigned to globalThis'}));\n"
        "  } else {\n"
        "    const validResults = VALID.map(c => [c, globalThis.__validateCNPJ(c)]);\n"
        "    const invalidResults = INVALID.map(c => [c, globalThis.__validateCNPJ(c)]);\n"
        "    process.stdout.write(JSON.stringify({ok: true, valid: validResults, invalid: invalidResults}));\n"
        "  }\n"
        "} catch (e) {\n"
        "  process.stdout.write(JSON.stringify({ok: false, error: String(e && e.message || e)}));\n"
        "}\n"
    )
    proc = subprocess.run(
        [node, "-e", runner, js_source, valid_literal, invalid_literal],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"node exited with code {proc.returncode}: {proc.stderr}"
        )
    payload = _json.loads(proc.stdout)
    if not payload.get("ok"):
        pytest.fail(
            "RED — validateCNPJ was extracted but is not valid JS "
            f"or did not assign to globalThis: {payload.get('error')}. "
            f"AC#4 canary failed. File: {INDEX_TS_PATH}"
        )

    for cnpj, result in payload["valid"]:
        assert result is True, (
            f"RED — validateCNPJ({cnpj!r}) returned {result!r}, but "
            "this is a known-valid CNPJ. The mod-11 implementation is "
            f"incorrect. AC#4 canary. File: {INDEX_TS_PATH}"
        )

    for cnpj, result in payload["invalid"]:
        assert result is False, (
            f"RED — validateCNPJ({cnpj!r}) returned {result!r}, but "
            "this is a known-INVALID CNPJ. The mod-11 implementation "
            f"is incorrect. AC#4 canary. File: {INDEX_TS_PATH}"
        )


# ── AC#5 ─────────────────────────────────────────────────────────────────────


def test_ac5_extract_phone_function_handles_br_formats():
    """AC#5 — ``extractPhone()`` extrai telefones BR (10-11 dígitos).

    GOAL:
        A função ``extractPhone()`` deve existir e capturar telefones
        brasileiros nos formatos:
            - (11) 99999-8888   (com pontuação)
            - 11999998888        (sem pontuação)
            - +55 11 99999-8888  (com código de país, opcional)

    BEHAVIOR:
        Dado um HTML com qualquer um desses formatos, ``extractPhone()``
        deve retornar uma string representando o telefone
        (provavelmente normalizado para 10-11 dígitos).

    AC#5:
        - ``extractPhone`` está declarada.
        - O corpo da função tem um regex com ``\d`` que casa 10-11
          dígitos (com ou sem pontuação).
        - O corpo retorna a string do match (``return match[0]`` /
          ``return m[0]`` / similar) e não apenas ``return null``.
    """
    source = _read_index_ts()
    assert _function_is_declared(source, "extractPhone"), (
        "RED — function `extractPhone` is NOT declared in "
        f"onboarding-website-intel/index.ts. AC#5 requires a function "
        "to extract BR phone numbers. File: {INDEX_TS_PATH}"
    )

    body = _extract_function_body(source, "extractPhone")

    # The body must reference a phone-shaped regex: 10-11 digits,
    # with optional separators. Look for ``\d`` patterns of length
    # 10 or 11.
    has_phone_digits_10 = re.search(r"\\d\{10\}", body)
    has_phone_digits_11 = re.search(r"\\d\{11\}", body)
    has_phone_digits_10_11 = re.search(r"\\d\{10,11\}", body)
    has_phone_pattern = (
        has_phone_digits_10
        or has_phone_digits_11
        or has_phone_digits_10_11
        or re.search(r"\(\d\{2\}\)", body)  # (11) style
        or re.search(r"99999-8888", body)
        or re.search(r"\\d\{4,5\}-\\d\{4\}", body)  # 9999-8888 or 99999-8888
    )
    assert has_phone_pattern, (
        "RED — extractPhone is declared but its regex does NOT match "
        "BR phone numbers (10-11 digits, with or without "
        "punctuation). AC#5 requires handling formats like "
        "``(11) 99999-8888`` and ``11999998888``. "
        f"File: {INDEX_TS_PATH}"
    )

    has_meaningful_return = re.search(
        r"return\s+(?:null|\"|'|`|[A-Za-z_\[])", body
    )
    assert has_meaningful_return, (
        "RED — extractPhone is declared but has no meaningful return "
        "statement. AC#5 requires returning the matched phone string "
        "(e.g. ``return match ? match[0] : null;``). "
        f"File: {INDEX_TS_PATH}"
    )


# ── AC#6 ─────────────────────────────────────────────────────────────────────


def test_ac6_detect_vertical_has_5_new_keywords():
    """AC#6 — ``detectVertical()`` detecta 5 novas verticais.

    GOAL:
        A função ``detectVertical()`` deve detectar as 5 novas
        verticais: ``design``, ``buffet``, ``construcao``,
        ``logistica``, ``consultoria``.

    BEHAVIOR:
        Para cada nova keyword, o site que contém o termo no texto
        visível deve ser classificado na vertical correspondente
        (que pode ser uma vertical nova ou reaproveitar uma já
        existente — desde que o teste do regex passe).

    AC#6:
        - As 5 keywords aparecem no corpo de ``detectVertical``.
        - Cada keyword está ligada a um ``return "VERTICAL"``
          específico (não em comentário ou texto solto).
    """
    source = _read_index_ts()
    body = _extract_function_body(source, "detectVertical")

    missing_in_body: list[str] = []
    unwired: list[str] = []
    for kw in NEW_VERTICAL_KEYWORDS:
        if not re.search(re.escape(kw), body):
            missing_in_body.append(kw)
        else:
            # The keyword is in the body; verify it is wired to a
            # specific vertical return value.
            vertical = _detect_vertical_keyword(source, kw)
            if vertical is None:
                unwired.append(kw)

    assert not missing_in_body, (
        "RED — detectVertical() does NOT contain the required new "
        "keywords: "
        f"{', '.join(missing_in_body)}. "
        "AC#6 requires detectVertical to support these 5 new "
        "verticals: design, buffet, construcao, logistica, "
        f"consultoria. File: {INDEX_TS_PATH}"
    )
    assert not unwired, (
        "RED — the following new keywords are present in detectVertical "
        "but NOT mapped to a vertical return value: "
        f"{', '.join(unwired)}. "
        "AC#6 requires each keyword to be inside a regex branch that "
        "returns a specific vertical (e.g. ``return \"design\";``). "
        f"File: {INDEX_TS_PATH}"
    )


# ── AC#7 ─────────────────────────────────────────────────────────────────────


def test_ac7_confidence_scoring_is_dynamic():
    """AC#7 — Confidence scoring dinâmico baseado no número de fontes.

    GOAL:
        A confidence da resposta deve ser calculada dinamicamente
        com base no número de fontes de sinal detectadas:

            1 fonte   → 0.3
            2 fontes  → 0.5
            3+ fontes → 0.7

    BEHAVIOR:
        Quanto mais sinais diferentes forem extraídos (CNPJ,
        telefone, vertical detectada, etc.), maior a confidence.

    AC#7:
        - Os valores ``0.3``, ``0.5`` e ``0.7`` aparecem no source.
        - O valor antigo ``vertical ? 0.72 : 0.45`` não aparece mais.
        - Há uma expressão que conta o número de fontes (ex:
          ``sourceCount``, ``sources.length``, ``numSources``).
    """
    source = _read_index_ts()

    # All three tier values must appear in the file.
    for value in ("0.3", "0.5", "0.7"):
        assert value in source, (
            f"RED — confidence tier value {value} is NOT present in "
            f"onboarding-website-intel/index.ts. AC#7 requires the "
            "dynamic scoring tiers 0.3 / 0.5 / 0.7. "
            f"File: {INDEX_TS_PATH}"
        )

    # The old hard-coded ``confidence: vertical ? 0.72 : 0.45`` must
    # be gone.
    assert "vertical ? 0.72 : 0.45" not in source, (
        "RED — confidence is still hard-coded to "
        "``vertical ? 0.72 : 0.45``. AC#7 requires dynamic scoring "
        "(1 fonte=0.3, 2=0.5, 3+=0.7). "
        f"File: {INDEX_TS_PATH}"
    )

    # Look for a source-counting expression.
    source_count_patterns = (
        r"\bsourceCount\b",
        r"\bsources\.length\b",
        r"\bnumSources\b",
        r"\bsource_count\b",
        r"\.length\s*[<>=!]+\s*[123]\b",  # 1/2/3 branches on length
    )
    has_source_counting = any(
        re.search(p, source) for p in source_count_patterns
    )
    assert has_source_counting, (
        "RED — no source-counting expression found. AC#7 requires "
        "the confidence to be derived from a counter of detected "
        "sources (e.g. ``sourceCount``, ``sources.length``, "
        f"``numSources``). File: {INDEX_TS_PATH}"
    )


# ── AC#8 ─────────────────────────────────────────────────────────────────────


def test_ac8_timeout_is_10000ms():
    """AC#8 — Timeout do ``fetch`` interno deve ser 10.000ms.

    GOAL:
        O ``setTimeout`` que aborta o ``fetch`` deve usar 10.000ms
        (e não mais 5.000ms).

    BEHAVIOR:
        Sites lentos têm mais tempo de resposta antes de o
        ``AbortController`` cancelar a requisição.

    AC#8:
        - ``setTimeout(() => controller.abort(), 10000)`` aparece no
          source.
        - O timeout antigo de 5.000ms não está mais presente.
    """
    source = _read_index_ts()
    assert "setTimeout(() => controller.abort(), 10000)" in source, (
        "RED — fetch timeout is NOT 10000ms. AC#8 requires "
        "``setTimeout(() => controller.abort(), 10000)`` in "
        f"onboarding-website-intel/index.ts. File: {INDEX_TS_PATH}"
    )
    assert "setTimeout(() => controller.abort(), 5000)" not in source, (
        "RED — old 5000ms timeout is still present. AC#8 requires "
        f"the 10000ms timeout. File: {INDEX_TS_PATH}"
    )


# ── AC#9 ─────────────────────────────────────────────────────────────────────


def test_ac9_empty_url_returns_zero_confidence_with_new_fields():
    """AC#9 — URL vazia retorna ``confidence: 0`` e novos campos.

    GOAL:
        Quando ``normalizeUrl()`` retorna string vazia
        (URL ausente ou inválida), a edge function deve retornar
        ``confidence: 0`` E os novos campos ``cnpj``,
        ``telefone``, ``confidence_details``.

    BEHAVIOR:
        Cliente envia ``POST { "website_url": "" }`` →
        resposta inclui ``confidence: 0``, ``cnpj: null``,
        ``telefone: null`` e ``confidence_details: {...}``.

    AC#9:
        - O bloco ``if (!normalized) { ... }`` está presente.
        - Dentro desse bloco, a resposta inclui ``confidence: 0``
          E os campos ``cnpj``, ``telefone`` e
          ``confidence_details``.
    """
    source = _read_index_ts()

    # The if-block must exist.
    assert "if (!normalized)" in source, (
        "RED — block `if (!normalized)` is NOT present. AC#9 "
        "requires explicit handling of empty / invalid URLs. "
        f"File: {INDEX_TS_PATH}"
    )

    # Find the body of the if-block: from ``if (!normalized)`` up to
    # the matching closing brace.
    if_idx = source.find("if (!normalized)")
    brace_start = source.find("{", if_idx)
    assert brace_start != -1, "Could not find opening brace of if-block"

    depth = 0
    end = -1
    for i in range(brace_start, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    assert end != -1, "Could not find closing brace of if (!normalized) block"
    if_body = source[brace_start:end]

    # The block must return ``confidence: 0``.
    assert re.search(r"confidence\s*:\s*0\b", if_body), (
        "RED — block `if (!normalized)` does NOT return "
        "``confidence: 0``. AC#9 requires confidence=0 for empty URL. "
        f"File: {INDEX_TS_PATH}"
    )

    # The block must include the new fields.
    for field in ("cnpj", "telefone", "confidence_details"):
        assert re.search(
            r"(?:^|[\s{,])" + re.escape(field) + r"\s*:",
            if_body,
            re.MULTILINE,
        ), (
            f"RED — field `{field}` is NOT a JSON key inside the "
            "``if (!normalized)`` block. AC#9 requires the empty-URL "
            "response to include cnpj, telefone and confidence_details "
            f"in addition to confidence: 0. File: {INDEX_TS_PATH}"
        )


# ── AC#10 ────────────────────────────────────────────────────────────────────


def test_ac10_spa_fallback_returns_graceful_response():
    """AC#10 — SPA / fetch vazio → fallback gracioso com novos campos.

    GOAL:
        Quando o ``fetch`` falha (timeout, network error, 5xx) ou
        retorna HTML vazio (SPA sem server-side rendering), a edge
        function deve cair em um fallback gracioso via try/catch —
        nunca em 500/crash — e a resposta de fallback deve incluir
        ``cnpj``, ``telefone`` e ``confidence_details``.

    BEHAVIOR:
        - ``try { await fetch(...) } catch { /* fallback */ }`` em
          torno do fetch interno.
        - O fallback retorna um JSON com ``cnpj``, ``telefone`` e
          ``confidence_details`` (além das chaves atuais).

    AC#10:
        - Existe um ``try`` imediatamente antes de ``await fetch(``.
        - Existe um ``catch`` que lida com erros do fetch.
        - Dentro do ``catch`` (ou do bloco de fallback), a resposta
          retornada inclui os novos campos ``cnpj``, ``telefone`` e
          ``confidence_details``.
    """
    source = _read_index_ts()

    # Find the fetch call.
    fetch_idx = source.find("await fetch(")
    assert fetch_idx != -1, (
        f"Could not find 'await fetch(' in {INDEX_TS_PATH}"
    )

    # There must be a ``try`` block immediately before the fetch.
    preceding = source[max(0, fetch_idx - 200):fetch_idx]
    assert "try" in preceding, (
        "RED — no `try` block found immediately before `await fetch(`. "
        "AC#10 requires a try/catch around the fetch to handle SPA / "
        f"network errors gracefully. File: {INDEX_TS_PATH}"
    )

    # There must be a ``catch`` block somewhere after the fetch
    # (handles the failure path).
    after_fetch = source[fetch_idx:fetch_idx + 1500]
    assert "catch" in after_fetch, (
        "RED — no `catch` block found after `await fetch(`. AC#10 "
        "requires a try/catch around the fetch to return a graceful "
        f"fallback. File: {INDEX_TS_PATH}"
    )

    # Extract the catch block: find the ``catch`` keyword after the
    # fetch and walk to the matching closing brace.
    catch_idx = source.find("catch", fetch_idx)
    assert catch_idx != -1, (
        "Could not locate `catch` after fetch in source"
    )

    brace_start = source.find("{", catch_idx)
    assert brace_start != -1, "Could not find opening brace of catch block"

    depth = 0
    end = -1
    for i in range(brace_start, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    assert end != -1, "Could not find closing brace of catch block"
    catch_body = source[brace_start:end]

    # The catch / fallback response must include the new fields.
    for field in ("cnpj", "telefone", "confidence_details"):
        assert re.search(
            r"(?:^|[\s{,])" + re.escape(field) + r"\s*:",
            catch_body,
            re.MULTILINE,
        ), (
            f"RED — field `{field}` is NOT a JSON key inside the "
            "catch / fallback block. AC#10 requires the SPA / "
            "fetch-error fallback response to include cnpj, "
            "telefone and confidence_details. "
            f"File: {INDEX_TS_PATH}"
        )
