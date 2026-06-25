"""RED test for onboarding-website-intel edge function expansion.

GOAL:
    Expandir a edge function ``supabase/functions/onboarding-website-intel/index.ts``
    com:
        - Novas verticais detectáveis (design, buffet, construcao, logistica,
          consultoria, advocacia, imobiliari, seguro, turismo, alimenta,
          transporte, beleza, fitness, oficina, engenharia, marketing, ti)
        - Extração de CNPJ e telefone a partir do HTML
        - Validação de CNPJ via dígitos verificadores
        - Confidence scoring dinâmico baseado no número de fontes
        - Campo ``confidence_details`` na resposta
        - Timeout de 10.000ms
        - Retrocompatibilidade com a resposta atual
            (``company_name``, ``vertical``, ``confidence`` etc.)

BEHAVIOR:
    B8 — Expansão da edge function ``onboarding-website-intel``.

AC (Acceptance Criteria):
    AC#1 — ``detectVertical()`` deve aceitar as novas keywords:
            design, buffet, construcao, logistica, consultoria, advocacia,
            imobiliari, seguro, turismo, alimenta, transporte, beleza,
            fitness, oficina, engenharia, marketing, ti.
    AC#2 — ``extractCNPJ()`` deve existir como função no arquivo.
    AC#3 — ``extractPhone()`` deve existir como função no arquivo.
    AC#4 — Confidence scoring dinâmico:
              1 fonte  → 0.3
              2 fontes → 0.5
              3+ fontes → 0.7
    AC#5 — ``validateCNPJ()`` deve existir e implementar o algoritmo de
            dígitos verificadores (mod-11 padrão CNPJ).
    AC#6 — Timeout do ``fetch`` interno deve ser 10.000ms
            (state RED atual: 5.000ms).
    AC#7 — Resposta JSON deve incluir ``cnpj``, ``telefone`` e
            ``confidence_details`` (sem quebrar o shape atual).
    AC#8 — Retrocompatibilidade: ``company_name``, ``vertical``,
            ``suggested_agents``, ``suggested_routines``,
            ``suggested_kpis`` e ``confidence`` devem continuar
            presentes na resposta.

DECISION:
    Estratégia: extend — editar
    ``supabase/functions/onboarding-website-intel/index.ts`` in-place.
    Nenhum arquivo novo deve ser criado. As funções novas
    (``extractCNPJ``, ``extractPhone``, ``validateCNPJ``) são adicionadas
    ao mesmo arquivo. ``detectVertical`` é estendido com as novas
    keywords.

Anti-Goals (must NOT be violated):
    1. NÃO substituir a implementação de ``stripHtml`` / ``normalizeUrl``
       (são utilitários corretos).
    2. NÃO alterar a assinatura pública de ``Deno.serve`` — a função
       continua recebendo ``Request`` e retornando ``Response``.
    3. NÃO remover ``suggestFromVertical`` — é usado tanto no caminho
       feliz quanto no fallback de erro.
    4. NÃO alterar a forma do JSON de erro (chave ``error``).
    5. NÃO importar bibliotecas externas de validação de CNPJ — a
       implementação deve ser local ao arquivo, sem novas deps.
    6. NÃO criar arquivos auxiliares em ``supabase/functions/_shared``
       para a expansão de website-intel — escopo restrito ao
       ``index.ts`` desta função.

Test strategy:
    Source inspection (lê o ``.ts`` como texto) porque ``Deno.serve()``
    inicia um listener de rede real quando executado, o que tornaria o
    teste flaky e dependente de runtime Deno. As funções puras
    (``detectVertical``, ``extractCNPJ``, ``extractPhone``,
    ``validateCNPJ``) são validadas via regex e/ou via extração +
    ``new Function(...)`` quando possível. Para ``validateCNPJ`` o teste
    inclui ainda uma canary-suite: executa a função extraída do source
    (sem rede, sem Deno) e verifica que aceita CNPJs válidos conhecidos
    e rejeita inválidos.

Estado atual (RED):
    - ``detectVertical`` NÃO contém as 17 novas keywords (apenas
      loja/e-commerce, distribuí, clínica, curso, contábil, serviço).
    - ``extractCNPJ`` NÃO está definida.
    - ``extractPhone`` NÃO está definida.
    - ``validateCNPJ`` NÃO está definida.
    - Timeout do ``fetch`` é 5000ms.
    - Resposta NÃO inclui ``cnpj``, ``telefone`` nem
      ``confidence_details``.
"""

from __future__ import annotations

import re
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

# Required new vertical keywords (AC#1).
NEW_VERTICAL_KEYWORDS: tuple[str, ...] = (
    "design",
    "buffet",
    "construcao",
    "logistica",
    "consultoria",
    "advocacia",
    "imobiliari",
    "seguro",
    "turismo",
    "alimenta",
    "transporte",
    "beleza",
    "fitness",
    "oficina",
    "engenharia",
    "marketing",
    "ti",
)


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
    # We only consider the very next ``return "..."`` after a matching
    # regex literal that contains the keyword.
    branch_pattern = re.compile(
        r"if\s*\(/\(([^)]+)\)/\.(?:test|exec|match)\([^)]+\)\)\s*return\s+\"([^\"]+)\""
    )
    for m in branch_pattern.finditer(body):
        regex_inner = m.group(1)
        vertical = m.group(2)
        if keyword in regex_inner:
            return vertical
    return None


# ── Tests ────────────────────────────────────────────────────────────────────


def test_b8_source_file_exists():
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


def test_b8_detect_vertical_has_new_keywords():
    """AC#1 — ``detectVertical()`` deve aceitar 17 novas keywords.

    Cada keyword deve estar em pelo menos um dos regexes de branch da
    função, mapeada para uma vertical específica (nova ou existente).

    RED state: nenhuma das 17 keywords está presente nos regexes
    atuais (apenas ``loja``, ``distribui``, ``clínica``, ``curso``,
    ``contabil``, ``serviço``).
    """
    source = _read_index_ts()
    body = _extract_function_body(source, "detectVertical")

    missing: list[str] = []
    for kw in NEW_VERTICAL_KEYWORDS:
        if not re.search(re.escape(kw), body):
            missing.append(kw)

    assert not missing, (
        "RED — detectVertical() does NOT contain the required new "
        "keywords. Behavior B8 / AC#1 requires these keywords to be "
        "wired into one of the regex branches: "
        f"{', '.join(missing)}. "
        f"File: {INDEX_TS_PATH}"
    )


def test_b8_detect_vertical_keywords_have_unique_mappings():
    """AC#1 — each new keyword must map to a vertical return value.

    A keyword is considered "wired" if it appears in a regex branch that
    returns a specific vertical string. This guarantees the keyword is
    not just present in a comment or unrelated context.
    """
    source = _read_index_ts()
    unwired: list[str] = []
    for kw in NEW_VERTICAL_KEYWORDS:
        vertical = _detect_vertical_keyword(source, kw)
        if vertical is None:
            unwired.append(kw)

    assert not unwired, (
        "RED — the following new keywords are present in detectVertical "
        "but NOT mapped to a vertical return value: "
        f"{', '.join(unwired)}. "
        "Each keyword must appear inside a regex branch that returns "
        "a specific vertical (e.g. ``return \"design\";``). "
        f"File: {INDEX_TS_PATH}"
    )


# ── AC#2 ─────────────────────────────────────────────────────────────────────


def test_b8_extract_cnpj_function_exists():
    """AC#2 — ``extractCNPJ()`` deve existir como função no arquivo.

    A função deve receber argumentos (input HTML/text) e retornar o
    CNPJ extraído (string) ou ``null``.
    """
    source = _read_index_ts()
    assert _function_is_declared(source, "extractCNPJ"), (
        "RED — function `extractCNPJ` is NOT declared in "
        f"onboarding-website-intel/index.ts. File: {INDEX_TS_PATH}"
    )

    body = _extract_function_body(source, "extractCNPJ")
    # The function must actually do something with the input: must
    # either return a string/number or null. A bare ``return;`` is
    # not acceptable.
    has_meaningful_return = re.search(
        r"return\s+(?:null|\"|'|`|[A-Za-z_])", body
    )
    assert has_meaningful_return, (
        "RED — extractCNPJ is declared but has no meaningful return "
        "statement. Expected something like "
        "``return match ? match[0] : null;`` or ``return null;``. "
        f"File: {INDEX_TS_PATH}"
    )


# ── AC#3 ─────────────────────────────────────────────────────────────────────


def test_b8_extract_phone_function_exists():
    """AC#3 — ``extractPhone()`` deve existir como função no arquivo.

    Semelhante a ``extractCNPJ``, deve retornar uma string de telefone
    (BR: 10-11 dígitos) ou ``null``.
    """
    source = _read_index_ts()
    assert _function_is_declared(source, "extractPhone"), (
        "RED — function `extractPhone` is NOT declared in "
        f"onboarding-website-intel/index.ts. File: {INDEX_TS_PATH}"
    )

    body = _extract_function_body(source, "extractPhone")
    has_meaningful_return = re.search(
        r"return\s+(?:null|\"|'|`|[A-Za-z_])", body
    )
    assert has_meaningful_return, (
        "RED — extractPhone is declared but has no meaningful return "
        "statement. Expected something like "
        "``return match ? match[0] : null;`` or ``return null;``. "
        f"File: {INDEX_TS_PATH}"
    )


# ── AC#4 ─────────────────────────────────────────────────────────────────────


def test_b8_confidence_scoring_is_dynamic():
    """AC#4 — Confidence scoring dinâmico baseado no número de fontes.

    Especificação:
        1 fonte  → 0.3
        2 fontes → 0.5
        3+ fontes → 0.7

    O source deve evidenciar essa lógica — procuramos por uma
    expressão de contagem de fontes (variável que represente o número
    de fontes encontradas) combinada com os valores mágicos 0.3, 0.5
    e 0.7.
    """
    source = _read_index_ts()

    # All three tier values must appear in the file.
    for value in ("0.3", "0.5", "0.7"):
        assert value in source, (
            f"RED — confidence tier value {value} is NOT present in "
            f"onboarding-website-intel/index.ts. Behavior B8 / AC#4 "
            "requires the dynamic scoring with tiers 0.3 / 0.5 / 0.7. "
            f"File: {INDEX_TS_PATH}"
        )

    # The old hard-coded ``confidence: vertical ? 0.72 : 0.45`` must
    # be gone — retrocompatibilidade is preserved by AC#8 (the key
    # `confidence` must exist), but the VALUE should come from the
    # dynamic scorer.
    assert "vertical ? 0.72 : 0.45" not in source, (
        "RED — confidence is still hard-coded to "
        "``vertical ? 0.72 : 0.45``. Behavior B8 / AC#4 requires "
        "dynamic scoring (1=0.3, 2=0.5, 3+=0.7). "
        f"File: {INDEX_TS_PATH}"
    )

    # Look for a source-counting expression: either ``sourceCount``,
    # ``sources.length``, ``numSources`` or similar.
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
        "RED — no source-counting expression found. Behavior B8 / "
        "AC#4 requires the confidence to be derived from a counter "
        "of detected sources (e.g. ``sourceCount``, "
        "``sources.length``, ``numSources``). "
        f"File: {INDEX_TS_PATH}"
    )


# ── AC#5 ─────────────────────────────────────────────────────────────────────


def test_b8_validate_cnpj_function_exists_with_check_digits():
    """AC#5 — ``validateCNPJ()`` deve existir e validar dígitos verificadores.

    A função deve:
        * Ser declarada como ``function validateCNPJ(...)``.
        * Implementar o algoritmo mod-11 do CNPJ (multiplicar pelos
          pesos [5,4,3,2,9,8,7,6,5,4,3,2] para DV1 e
          [6,5,4,3,2,9,8,7,6,5,4,3,2] para DV2).
        * Aceitar CNPJs válidos e rejeitar inválidos.
    """
    source = _read_index_ts()
    assert _function_is_declared(source, "validateCNPJ"), (
        "RED — function `validateCNPJ` is NOT declared in "
        f"onboarding-website-intel/index.ts. File: {INDEX_TS_PATH}"
    )

    body = _extract_function_body(source, "validateCNPJ")
    # The function must reference mod-11 via ``% 11``.
    assert "% 11" in body or "%11" in body, (
        "RED — validateCNPJ is declared but does NOT implement the "
        "mod-11 check digit algorithm. Expected something like "
        "``const rest = sum % 11; const dv = rest < 2 ? 0 : 11 - rest;``. "
        f"File: {INDEX_TS_PATH}"
    )

    # The function must reference both digit-verifier positions
    # (CNPJ has 12 base digits + DV1 + DV2 = 14 total).
    assert "dv1" in body.lower() and "dv2" in body.lower(), (
        "RED — validateCNPJ must compute both DV1 and DV2 (the two "
        "check digits of a CNPJ). Expected variables named ``dv1`` "
        "and ``dv2`` (or equivalent) in the function body. "
        f"File: {INDEX_TS_PATH}"
    )


# ── AC#6 ─────────────────────────────────────────────────────────────────────


def test_b8_timeout_is_10000ms():
    """AC#6 — Timeout do ``fetch`` interno deve ser 10.000ms.

    RED state: timeout atual é 5.000ms
    (``setTimeout(() => controller.abort(), 5000)``).
    """
    source = _read_index_ts()
    assert "setTimeout(() => controller.abort(), 10000)" in source, (
        "RED — fetch timeout is NOT 10000ms. Behavior B8 / AC#6 "
        "requires ``setTimeout(() => controller.abort(), 10000)`` "
        "in onboarding-website-intel/index.ts. "
        f"File: {INDEX_TS_PATH}"
    )
    # Make sure the old 5000ms timeout is gone.
    assert "setTimeout(() => controller.abort(), 5000)" not in source, (
        "RED — old 5000ms timeout is still present. Behavior B8 / "
        "AC#6 requires the 10000ms timeout. "
        f"File: {INDEX_TS_PATH}"
    )


# ── AC#7 ─────────────────────────────────────────────────────────────────────


def test_b8_response_includes_cnpj_phone_and_confidence_details():
    """AC#7 — Resposta JSON deve incluir ``cnpj``, ``telefone`` e
    ``confidence_details``.

    Esses campos devem aparecer como chaves em um dos ``return json``
    do handler principal (caminho feliz ou fallback de erro).

    Aceita ``cnpj: ...``, ``"cnpj": ...`` ou
    ``... cnpj, telefone, confidence_details ...``.
    """
    source = _read_index_ts()

    missing: list[str] = []
    for field in ("cnpj", "telefone", "confidence_details"):
        if field not in source:
            missing.append(field)

    assert not missing, (
        "RED — the response payload is missing required fields: "
        f"{', '.join(missing)}. Behavior B8 / AC#7 requires the JSON "
        "response to include `cnpj`, `telefone` and "
        "``confidence_details`` in addition to the existing keys. "
        f"File: {INDEX_TS_PATH}"
    )

    # Each field must appear as an object key (preceded by ``{``,
    # ``,`` or whitespace, and followed by ``:``).
    for field in ("cnpj", "telefone", "confidence_details"):
        pattern = r"(?:^|[\s{,])" + re.escape(field) + r"\s*:"
        assert re.search(pattern, source, re.MULTILINE), (
            f"RED — field `{field}` is mentioned in the file but is "
            "NOT a JSON key in the response payload. Expected "
            f"``{field}: ...`` to appear in a ``return json(...)`` "
            f"block. File: {INDEX_TS_PATH}"
        )


# ── AC#8 ─────────────────────────────────────────────────────────────────────


def test_b8_backwards_compatible_response_keys():
    """AC#8 — Retrocompatibilidade: as chaves atuais da resposta devem
    continuar presentes.

    O payload atual (RED) inclui:
        ``company_name``, ``vertical``, ``suggested_size``,
        ``suggested_agents``, ``suggested_routines``,
        ``suggested_kpis``, ``confidence``.

    A expansão de AC#7 (cnpj, telefone, confidence_details) é
    aditiva — nenhum campo existente pode ser removido.
    """
    source = _read_index_ts()
    preserved_keys: tuple[str, ...] = (
        "company_name",
        "vertical",
        "suggested_size",
        "suggested_agents",
        "suggested_routines",
        "suggested_kpis",
        "confidence",
    )

    missing: list[str] = []
    for key in preserved_keys:
        if not re.search(
            r"(?:^|[\s{,])" + re.escape(key) + r"\s*:",
            source,
            re.MULTILINE,
        ):
            missing.append(key)

    assert not missing, (
        "RED — backwards-compatible response keys are missing from "
        f"onboarding-website-intel/index.ts: {', '.join(missing)}. "
        "Behavior B8 / AC#8 requires these keys to be preserved in "
        "every ``return json(...)`` block. The new fields (cnpj, "
        "telefone, confidence_details) are additive and must not "
        "remove any existing key. "
        f"File: {INDEX_TS_PATH}"
    )


# ── Canary suite: validateCNPJ accepts known valid and rejects invalid ──────


def test_b8_validate_cnpj_canary_executes_correct_algorithm():
    """AC#5 (canary) — Executa a ``validateCNPJ`` extraída do source e
    verifica comportamento real.

    Quando a função existir e implementar o algoritmo mod-11 do CNPJ,
    este teste extrai a função do source, compila com ``new Function``
    e roda contra CNPJs conhecidos:
        * Válido: 11.222.333/0001-81 (CNPJ de teste público)
        * Válido: 04.337.168/0001-58 (CNPJ Bradesco - público)
        * Inválido: 11.222.333/0001-82 (DV1 errado)
        * Inválido: 00.000.000/0000-00 (todos zeros)

    RED state: a função não existe, então a extração falha em
    ``_extract_function_body`` e a asserção explode com a mensagem RED.
    """
    import json as _json
    import shutil
    import subprocess

    source = _read_index_ts()
    body = _extract_function_body(source, "validateCNPJ")

    # Turn ``function validateCNPJ(input) { ... }`` into
    # ``globalThis.__validateCNPJ = function(input) { ... }`` so the
    # Node subprocess can expose it as ``globalThis.__validateCNPJ``.
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
            "validateCNPJ canary. Install Node.js to enable the "
            "canary suite for AC#5."
        )

    # Run a small Node script that (1) compiles the function above,
    # (2) calls it against the test vectors, (3) prints JSON.
    valid_cnpjs = (
        "11222333000181",
        "04337168000158",
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
            f"File: {INDEX_TS_PATH}"
        )

    for cnpj, result in payload["valid"]:
        assert result is True, (
            f"RED — validateCNPJ({cnpj!r}) returned {result!r}, but "
            "this is a known-valid CNPJ. The mod-11 implementation is "
            f"incorrect. File: {INDEX_TS_PATH}"
        )

    for cnpj, result in payload["invalid"]:
        assert result is False, (
            f"RED — validateCNPJ({cnpj!r}) returned {result!r}, but "
            "this is a known-INVALID CNPJ. The mod-11 implementation "
            f"is incorrect. File: {INDEX_TS_PATH}"
        )
