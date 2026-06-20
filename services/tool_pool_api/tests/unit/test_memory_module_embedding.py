# services/tool_pool_api/tests/unit/test_memory_module_embedding.py
"""Testes unitarios do _build_embedding_text e hook de embedding (T3.1f Secoes 2 e 3).

Usa extração isolada das funções (sem disparar a cadeia de imports do tool_pool_api).
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper: load a single function from memory_module.py source
# ---------------------------------------------------------------------------


def _extract_function(source: str, func_name: str, extra_globals: dict | None = None):
    """Extracts a function from Python source code into a clean namespace."""
    marker = f"def {func_name}("
    idx = source.find(marker)
    if idx == -1:
        raise ValueError(f"Could not find '{func_name}' in source")

    # Find start of the def line
    fn_start = source.rfind("\n", 0, idx) + 1 if idx > 0 else 0

    # Collect all lines from fn_start forward
    remaining = source[fn_start:]
    lines = remaining.split("\n")

    fn_lines = []
    found_def = False
    # Track if we're still in the signature (parens not closed)
    in_signature = False
    paren_depth = 0

    for line in lines:
        stripped = line.strip()

        if not found_def:
            if f"def {func_name}(" in stripped:
                found_def = True
                fn_lines.append(line)
                # Check if signature ends on this line
                sig_part = line[line.index(f"def {func_name}("):]
                paren_depth = sig_part.count("(") - sig_part.count(")")
                in_signature = paren_depth > 0
            continue

        # Inside function
        if in_signature:
            fn_lines.append(line)
            paren_depth += stripped.count("(") - stripped.count(")")
            if paren_depth <= 0:
                in_signature = False
            continue

        # Function body — detect end by indentation
        if stripped == "":
            fn_lines.append("")
            continue

        current_indent = len(line) - len(line.lstrip())
        if current_indent == 0 and stripped:
            # Top-level line after function = function ended
            break

        fn_lines.append(line)

    namespace = {"__name__": f"extracted_{func_name}"}
    if extra_globals:
        namespace.update(extra_globals)
    exec("\n".join(fn_lines), namespace)
    return namespace[func_name]


def _load_from_source():
    """Load _build_embedding_text and _try_generate_embedding from memory_module.py."""
    import logging
    import pathlib
    import time as time_module

    mod_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "src" / "tool_pool_api" / "server" / "tool_modules"
        / "memory_module.py"
    )
    source = mod_path.read_text()

    # _build_embedding_text is pure — no extra globals needed
    build_fn = _extract_function(source, "_build_embedding_text")

    # _try_generate_embedding needs logger, time, and _build_embedding_text
    extra = {
        "logger": logging.getLogger("test_memory_module"),
        "time": time_module,
        "_build_embedding_text": build_fn,
    }
    hook_fn = _extract_function(source, "_try_generate_embedding", extra_globals=extra)
    return build_fn, hook_fn


_build_embedding_text, _try_generate_embedding = _load_from_source()


# ---------------------------------------------------------------------------
# Section 2: Tests for _build_embedding_text
# ---------------------------------------------------------------------------


class TestBuildEmbeddingText:
    """Testes unitarios de _build_embedding_text (T3.1f Secao 2)."""

    def test_build_embedding_text_basic(self):
        """entity_type, entity_name, key incluidos."""
        text = _build_embedding_text(
            entity_type="client", entity_name="acme corp",
            key="preferencia_pagamento",
            value={"metodo": "transferencia_bancaria", "prazo": 30},
        )
        assert "Entity type: client" in text
        assert "Entity name: acme corp" in text
        assert "Key: preferencia_pagamento" in text
        assert "metodo: transferencia_bancaria" in text
        assert "prazo: 30" in text

    def test_build_embedding_text_with_category(self):
        """Category aparece no texto."""
        text = _build_embedding_text(
            entity_type="skill", entity_name="gerador",
            key="template", value={"desc": "template mensal"},
            category="knowledge",
        )
        assert "Category: knowledge" in text

    def test_build_embedding_text_skips_uuids(self):
        """snapshot_id, gerado_em etc NAO aparecem."""
        text = _build_embedding_text(
            entity_type="snapshot", entity_name="financeiro:mensal",
            key="2025-06",
            value={
                "snapshot_id": str(uuid.uuid4()),
                "gerado_em": "2025-06-15T10:00:00Z",
                "vigencia_inicio": "2025-06-01",
                "vigencia_fim": "2025-06-30",
                "versao": 3, "template_version": 2,
                "resumo_executivo": "Mes positivo com 12% crescimento",
            },
        )
        assert "snapshot_id" not in text
        assert "gerado_em" not in text
        assert "vigencia_inicio" not in text
        assert "vigencia_fim" not in text
        assert "versao" not in text
        assert "template_version" not in text
        assert "resumo_executivo" in text

    def test_build_embedding_text_truncates_long_fields(self):
        """Campos >500 chars truncados."""
        long_text = "A" * 800
        text = _build_embedding_text(
            entity_type="client", entity_name="big",
            key="desc", value={"bio": long_text},
        )
        assert "bio: " + "A" * 500 in text
        assert "A" * 501 not in text

    def test_build_embedding_text_numeric_fields(self):
        """Indicadores numericos incluidos, exceto confidence."""
        text = _build_embedding_text(
            entity_type="snapshot", entity_name="clientes:mensal",
            key="2025-06",
            value={"total_clientes": 1200, "ticket_medio": 450.75,
                   "nps": 85, "confidence": 0.95},
        )
        assert "total_clientes: 1200" in text
        assert "ticket_medio: 450.75" in text
        assert "nps: 85" in text
        assert "confidence" not in text


# ---------------------------------------------------------------------------
# Section 3: Tests for _try_generate_embedding hook
# ---------------------------------------------------------------------------


class TestEmbeddingHook:
    """Testes do hook _try_generate_embedding (T3.1f Secao 3)."""

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_upsert_generates_embedding(self, mock_post):
        """Mock Cohere, payload inclui embedding apos hook."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embeddings": {"float": [[0.5] * 384]}
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"CO_API_KEY": "test-key"}, clear=False):
            payload = {"client_id": str(uuid.uuid4()), "entity_type": "client",
                       "entity_name": "test", "key": "pref"}
            value = {"idioma": "pt-BR"}

            await _try_generate_embedding(
                entity_type="client", entity_name="test",
                key="pref", payload=payload, value=value,
            )

        assert "embedding" in payload
        assert len(payload["embedding"]) == 384

    @pytest.mark.asyncio
    async def test_upsert_without_cohere_skips_embedding(self):
        """ImportError do blu_llm_service segue sem embedding."""
        payload = {"client_id": str(uuid.uuid4()), "key": "teste"}
        value = {"dado": "valor"}

        with patch(
            "blu_llm_service.get_cohere_embedding_model",
            side_effect=ImportError("not installed"),
        ):
            await _try_generate_embedding(
                entity_type="client", entity_name="test",
                key="teste", payload=payload, value=value,
            )

        assert "embedding" not in payload

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_upsert_cohere_failure_does_not_block(self, mock_post):
        """API error log + segue, NAO bloqueia."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Cohere error")
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"CO_API_KEY": "test-key"}, clear=False):
            payload = {"client_id": str(uuid.uuid4()), "key": "teste"}
            value = {"dado": "valor"}

            # Nao deve lancar excecao
            await _try_generate_embedding(
                entity_type="client", entity_name="test",
                key="teste", payload=payload, value=value,
            )

        assert "embedding" not in payload

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_write_generates_embedding(self, mock_post):
        """Mesmo comportamento para write: embedding gerado."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embeddings": {"float": [[0.8] * 384]}
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"CO_API_KEY": "test-key"}, clear=False):
            payload = {"client_id": str(uuid.uuid4()), "key": "write_test"}
            value = {"msg": "hello"}

            await _try_generate_embedding(
                entity_type="user", entity_name="joao",
                key="write_test", payload=payload, value=value,
                category="knowledge",
            )

        assert "embedding" in payload
        assert len(payload["embedding"]) == 384
