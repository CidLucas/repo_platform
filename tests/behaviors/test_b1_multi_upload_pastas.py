"""RED test for behavior B-1 — Multi-upload e pastas (BKL-034).

GOAL:
    Implementar multi-upload de arquivos e upload de pastas na Biblioteca de Conhecimento.
    Criar uploadMulti() que aceita File[] com 1+ arquivos, suporta pastas via
    webkitdirectory, chama callback de progresso por arquivo e não aborta
    os demais arquivos quando um falha.

BEHAVIOR:
    B-1 — Multi-upload e pastas (BKL-034)
    O serviço `knowledgeBaseService.ts` deve exportar `uploadMulti()` que:
        - Aceita `files: File[]` e itera sobre cada arquivo chamando
          `uploadFile()` ou `uploadComplexFile()`
        - Aceita `options.folder?: string` para organizar uploads de pastas
        - Aceita `onProgress?: (file: File, idx: number, total: number) => void`
          chamado a cada arquivo processado
        - Não aborta os demais arquivos quando um lança erro
        - Retorna `Promise<{id: string; file: File; error?: string}[]>`

    O hook `useKnowledgeBase.ts` deve expor `uploadMulti()` com estado
    de progresso.

    O componente `BibliotecaRoom.tsx` deve ter input file com:
        - `multiple` para seleção de múltiplos arquivos
        - `webkitdirectory` para seleção de pastas

AC (Acceptance Criteria):
    AC#1 — knowledgeBaseService.ts exporta função uploadMulti()
    AC#2 — uploadMulti() aceita File[] com 1+ arquivos
    AC#3 — uploadMulti() aceita options.folder para pastas
    AC#4 — uploadMulti() chama onProgress callback por arquivo
    AC#5 — Erro em 1 arquivo não aborta os demais
    AC#6 — useKnowledgeBase.ts expõe uploadMulti()
    AC#7 — BibliotecaRoom.tsx tem input file com multiple
    AC#8 — BibliotecaRoom.tsx tem input file com webkitdirectory

Anti-Goals (must NOT be violated):
    1. NÃO modificar o comportamento de uploadFile()/uploadSimpleFile()/uploadComplexFile()
       existentes — são funções unitárias que devem continuar funcionando
    2. NÃO remover suporte a upload de arquivo único
    3. NÃO introduzir dependências externas novas (bibliotecas de upload)
    4. NÃO alterar a interface de KBState (useKnowledgeBase)

Estado atual: RED — uploadMulti() ainda não existe em knowledgeBaseService.ts,
useKnowledgeBase.ts, nem webkitdirectory/multiple no BibliotecaRoom.tsx.
"""

import re
from pathlib import Path

import pytest

# ── Paths ───────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

KB_SERVICE_PATH = (
    REPO_ROOT / "apps" / "blu_v3" / "src" / "services" / "knowledgeBaseService.ts"
)
USE_KB_PATH = (
    REPO_ROOT / "apps" / "blu_v3" / "src" / "hooks" / "useKnowledgeBase.ts"
)
BIBLIOTECA_PATH = (
    REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "BibliotecaRoom.tsx"
)


# ── Override root conftest cleanup (pure file-based test) ───────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file inspection, no DB."""
    yield


# ── AC#1: uploadMulti exportada no service ──────────────────────────────


def _service_source() -> str:
    assert KB_SERVICE_PATH.exists(), (
        f"knowledgeBaseService.ts não encontrado: {KB_SERVICE_PATH}"
    )
    return KB_SERVICE_PATH.read_text(encoding="utf-8")


def _hook_source() -> str:
    assert USE_KB_PATH.exists(), (
        f"useKnowledgeBase.ts não encontrado: {USE_KB_PATH}"
    )
    return USE_KB_PATH.read_text(encoding="utf-8")


def _biblioteca_source() -> str:
    assert BIBLIOTECA_PATH.exists(), (
        f"BibliotecaRoom.tsx não encontrado: {BIBLIOTECA_PATH}"
    )
    return BIBLIOTECA_PATH.read_text(encoding="utf-8")


# ── Tests ────────────────────────────────────────────────────────────────


def test_b1_ac1_service_exports_upload_multi():
    """AC#1 — knowledgeBaseService.ts deve exportar uploadMulti().

    Verifica que o arquivo contém ``export async function uploadMulti``
    ou ``export function uploadMulti``, indicando que a função foi
    implementada e exportada.
    """
    src = _service_source()

    assert re.search(
        r"export\s+(async\s+)?function\s+uploadMulti\s*\(",
        src,
    ), (
        "AC#1 RED: knowledgeBaseService.ts ainda não exporta a função "
        "uploadMulti(). Esperado encontrar:\n"
        "    export async function uploadMulti(\n"
        "no arquivo:\n"
        f"    {KB_SERVICE_PATH}\n\n"
        "O coder precisa criar uploadMulti() que aceite File[], iterando "
        "sobre cada arquivo com uploadFile()/uploadComplexFile()."
    )


def test_b1_ac2_upload_multi_accepts_file_array():
    """AC#2 — uploadMulti() deve aceitar File[] com 1+ arquivos.

    Verifica que a assinatura de uploadMulti inclui o parâmetro
    ``files: File[]`` ou ``files: File[``.
    """
    src = _service_source()

    # Procura a declaração de uploadMulti e verifica o primeiro parâmetro
    match = re.search(
        r"uploadMulti\s*\(\s*(files\s*:\s*(File\[\]|Array<File>))",
        src,
    )
    assert match, (
        "AC#2 RED: uploadMulti() não aceita File[] como parâmetro. "
        "Esperado:\n"
        "    export async function uploadMulti(\n"
        "      files: File[],\n"
        "      clientId: string,\n"
        "      ...\n"
        "    )\n\n"
        "A função deve aceitar um array de arquivos para upload em lote."
    )


def test_b1_ac3_upload_multi_accepts_folder_option():
    """AC#3 — uploadMulti() deve aceitar options.folder para pastas.

    Verifica que a função aceita um parâmetro de opções contendo
    ``folder`` (ex: ``options?: { folder?: string }`` ou similar).
    """
    src = _service_source()

    # A função deve ter 'folder' em algum lugar da definição ou options
    # Pode ser options.folder, UploadMultiOptions.folder, etc.
    assert re.search(
        r"folder\s*[?:]\s*string",
        src,
    ), (
        "AC#3 RED: uploadMulti() ou suas opções não suportam 'folder'. "
        "Esperado um parâmetro folder na interface de opções ou diretamente "
        "na função para organizar uploads de pastas via webkitdirectory. "
        "Exemplo:\n"
        "    interface UploadMultiOptions extends UploadOptions {\n"
        "      folder?: string\n"
        "      onProgress?: (file: File, idx: number, total: number) => void\n"
        "    }"
    )


def test_b1_ac4_upload_multi_calls_on_progress():
    """AC#4 — uploadMulti() deve chamar onProgress callback por arquivo.

    Verifica que o tipo/propriedade ``onProgress`` existe no escopo
    de uploadMulti (na interface de opções ou no corpo da função).
    Pode ser ``onProgress`` como callback na interface de opções ou
    ``onProgress?`` na declaração.
    """
    src = _service_source()

    assert re.search(
        r"onProgress\s*[?:]",
        src,
    ), (
        "AC#4 RED: uploadMulti() não possui callback onProgress. "
        "Esperado um callback de progresso chamado a cada arquivo "
        "processado. Exemplo:\n"
        "    onProgress?: (file: File, idx: number, total: number) => void\n\n"
        "O callback deve ser invocado a cada arquivo, permitindo que "
        "a UI mostre progresso individual."
    )


def test_b1_ac5_upload_multi_continues_on_error():
    """AC#5 — Erro em 1 arquivo não deve abortar os demais.

    Verifica que uploadMulti() contém lógica de try/catch individual
    por arquivo (não um único try/catch ao redor de todo lote),
    capturando erros de cada upload sem interromper os seguintes.
    """
    src = _service_source()

    # Procura por padrão de try/catch DENTRO de um loop (for/while/forEach)
    # que indica tratamento individual de erros por arquivo
    has_try_inside_loop = bool(
        re.search(r"(for|forEach|map|reduce)\s*[\(\(].*\bfile\b.*[\)\)]\s*[{=]\s*[^}]*?\btry\b", src, re.DOTALL)
    )
    # Alternativa: verifica se há catch dentro de uploadMulti
    has_catch_in_upload_multi = bool(
        re.search(r"uploadMulti[\s\S]{0,2000}\bcatch\b", src)
    )

    assert has_try_inside_loop or has_catch_in_upload_multi, (
        "AC#5 RED: uploadMulti() não trata erros individuais por arquivo. "
        "Cada iteração do loop deve ter try/catch próprio para que um "
        "erro em um arquivo não interrompa o upload dos demais. "
        "Exemplo:\n"
        "    for (const file of files) {\n"
        "      try {\n"
        "        const id = await uploadFile(file, clientId, ...)\n"
        "        results.push({ id, file })\n"
        "      } catch (err) {\n"
        "        results.push({ id: '', file, error: err.message })\n"
        "      }\n"
        "    }"
    )


def test_b1_ac6_hook_exposes_upload_multi():
    """AC#6 — useKnowledgeBase.ts deve expor uploadMulti().

    Verifica que o hook exporta um método ``uploadMulti`` no return
    do hook (ex: ``uploadMulti`` listado no objeto de retorno).
    """
    src = _hook_source()

    assert re.search(
        r"\buploadMulti\b",
        src,
    ), (
        "AC#6 RED: useKnowledgeBase.ts não expõe uploadMulti() no "
        "seu objeto de retorno. Esperado:\n"
        "    return {\n"
        "      ...state,\n"
        "      upload,\n"
        "      uploadMulti,  // <-- novo método\n"
        "      uploadCsv,\n"
        "      ...\n"
        "    }"
    )


def test_b1_ac7_biblioteca_has_multiple_input():
    """AC#7 — BibliotecaRoom.tsx deve ter input file com multiple.

    Verifica que o input file no componente tem o atributo ``multiple``
    (``<input ... multiple ... />`` ou ``multiple={true}``).
    """
    src = _biblioteca_source()

    assert re.search(
        r"\bmultiple\b",
        src,
    ), (
        "AC#7 RED: O input file em BibliotecaRoom.tsx não possui o "
        "atributo ``multiple``. Esperado no input type=file:\n"
        "    <input\n"
        "      type=\"file\"\n"
        "      multiple\n"
        "      ...\n"
        "    />\n\n"
        "O atributo multiple permite selecionar vários arquivos de uma vez."
    )


def test_b1_ac8_biblioteca_has_webkitdirectory():
    """AC#8 — BibliotecaRoom.tsx deve ter input file com webkitdirectory.

    Verifica que o input file no componente tem o atributo
    ``webkitdirectory`` (``webkitdirectory`` ou ``{webkitdirectory: true}``).
    """
    src = _biblioteca_source()

    assert re.search(
        r"\bwebkitdirectory\b",
        src,
    ), (
        "AC#8 RED: O input file em BibliotecaRoom.tsx não possui o "
        "atributo ``webkitdirectory``. Esperado no input type=file:\n"
        "    <input\n"
        "      type=\"file\"\n"
        "      webkitdirectory\n"
        "      ...\n"
        "    />\n\n"
        "webkitdirectory permite selecionar pastas inteiras no Chrome/Edge. "
        "Para Safari (que não suporta webkitdirectory), deve haver fallback "
        "para ``multiple`` apenas com hint visual."
    )
