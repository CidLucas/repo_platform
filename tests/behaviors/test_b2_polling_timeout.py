"""RED test for behavior B-2 — Adiciona timeout no polling do frontend.

GOAL:
    Documento que fica ``processing`` > 2 min deve parar de ser polado
    e exibir mensagem "Falha no processamento". Documento que completa
    dentro de 2 min deve parar de pollar normalmente.

BEHAVIOR:
    B-2 — Adiciona timeout no polling do frontend.

    After the fix:
    - O useEffect de polling (segundo useEffect em useKnowledgeBase.ts)
      deve iniciar um ``setTimeout`` de ``POLLING_TIMEOUT_MS`` (120 s).
    - Quando o timeout expirar (documento ainda ``processing``), deve
      parar o polling (``clearInterval``) e setar o estado de erro
      ``error: 'Falha no processamento'``.
    - Nao deve haver marcadores de merge conflict (``<<<<<<<``)
      residuais no arquivo.

AC (Acceptance Criteria):
    AC-2: Polling no frontend para apos 2 min se documento nao completar,
          exibindo "Falha no processamento".

Estado atual (antes da correcao) — o teste falha (RED) porque:
    - O arquivo useKnowledgeBase.ts contem marcadores de merge conflict
      ``<<<<<<< HEAD`` nas linhas 78-81.
    - A linha ``setState((prev) => ({ ...prev, error: 'Falha no processamento' }))``
      esta do lado ``=======`` / ``>>>>>>> origin/main``, nao ativa.
    - O HEAD esta vazio — o setTimeout apenas faz ``clearInterval``,
      sem exibir "Falha no processamento".
"""

import pathlib
import re

import pytest

# -- Paths -----------------------------------------------------------

_REPO_ROOT = pathlib.Path("/home/ec2-user/repo_platform")
_APP_SRC = _REPO_ROOT / "apps" / "blu_v3" / "src"

_KB_HOOK_PATH = _APP_SRC / "hooks" / "useKnowledgeBase.ts"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# -- Tests -----------------------------------------------------------


class TestB2PollingTimeout:
    """B-2: Adiciona timeout no polling do frontend — AC-2."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Sanity: production file must exist."""
        assert _KB_HOOK_PATH.is_file(), (
            f"Arquivo de producao nao encontrado em "
            f"{_KB_HOOK_PATH}. O teste de behavior B-2 pressupoe a "
            f"existencia do hook useKnowledgeBase.ts."
        )
        self._source = _read(_KB_HOOK_PATH)

    def test_polling_timeout_exibe_falha_processamento(self):
        """RED — AC-2: Polling timeout deve exibir 'Falha no processamento'.

        No estado DESEJADO (apos GREEN):
        - O arquivo NAO contem marcadores de merge conflict (<<<<<<<).
        - O callback do setTimeout (dentro do polling useEffect) contem
          ``setState((prev) => ({ ...prev, error: 'Falha no processamento' }))``.

        No estado ATUAL (RED):
        - O arquivo contem ``<<<<<<< HEAD`` nas linhas 78-81.
        - A linha de setState esta do lado ``=======``, nao ativa no HEAD.
        - O setTimeout apenas faz ``clearInterval(interval)``.

        A verificacao extrai o corpo do polling useEffect (comentario
        "// Poll while any document") e verifica se dentro dele o
        callback do setTimeout contem a linha esperada E nao ha
        marcadores de merge conflict.
        """
        # 1. Extrair o polling useEffect body (segundo useEffect,
        #    comentado com "// Poll while any document...")
        poll_start_match = re.search(
            r"// Poll while any document is in a transient state",
            self._source,
        )
        assert poll_start_match is not None, (
            "Nao encontrou o polling useEffect (comentario "
            "'// Poll while any document'). Sanity check falhou."
        )

        # O polling effect termina na linha
        #   "}, [state.documents, load])"
        # Busca a partir do inicio do efecto
        rest = self._source[poll_start_match.start():]
        effect_end_match = re.search(
            r"\},\s*\[state\.documents,\s*load\]\s*\)",
            rest,
        )
        assert effect_end_match is not None, (
            "Nao encontrou o fechamento do polling useEffect "
            "('}, [state.documents, load])'). Sanity check falhou."
        )
        polling_effect_body = rest[:effect_end_match.end()]

        # 2. Extrair o setTimeout callback dentro do polling effect
        timeout_match = re.search(
            r"const timeout = setTimeout\(\(\) => \{",
            polling_effect_body,
        )
        assert timeout_match is not None, (
            "Nao encontrou setTimeout dentro do polling useEffect. "
            "Sanity check falhou."
        )

        # Extrai o corpo do callback ate o }, POLLING_TIMEOUT_MS)
        cb_start = timeout_match.end()
        # Encontra o fechamento: "}, POLLING_TIMEOUT_MS)" ou "}, 120_000)"
        cb_end_match = re.search(
            r"\},\s*(?:POLLING_TIMEOUT_MS|120_000)\s*\)",
            polling_effect_body[cb_start:],
        )
        assert cb_end_match is not None, (
            "Nao encontrou fechamento do setTimeout. "
            "Sanity check falhou."
        )
        timeout_cb_body = polling_effect_body[cb_start:cb_start + cb_end_match.start()]

        # 3. ASSERT: timeout callback deve conter o setState de erro
        #    No estado atual (RED), isso falha porque o setState esta
        #    dentro do merge conflict e o callback so tem clearInterval
        has_falha = (
            "error: 'Falha no processamento'" in timeout_cb_body
            or 'error: "Falha no processamento"' in timeout_cb_body
        )
        assert has_falha, (
            "AC-2 FAIL (RED): O callback do setTimeout no polling "
            "useEffect NAO contem setState com "
            "'Falha no processamento'. "
            "O polling timeout deve exibir \"Falha no processamento\" "
            "para documentos que ficam em processing > 2 min. "
            f"Corpo atual do callback:\n{timeout_cb_body}"
        )

        # 4. ASSERT: nao deve haver merge conflict markers no arquivo
        #    No estado atual (RED), <<<<<<< HEAD existe → falha
        assert "<<<<<<<" not in self._source, (
            "AC-2 FAIL (RED): O arquivo useKnowledgeBase.ts contem "
            "marcadores de merge conflict (<<<<<<< HEAD). "
            "Resolva o merge conflict para que o codigo do timeout "
            "fique ativo."
        )
