"""RED test — B-4: Aba Documentos unificada — Ativos + rascunhos + modelos + gerador.

GOAL:
    Unificar ativos + rascunhos + modelos em uma única aba Documentos;
    integrar gerador de documentos com templates/modelos.

BEHAVIOR:
    "B-4: Aba Documentos unificada — Ativos + rascunhos + modelos + gerador de documentos."

    A EstrategiaRoom atual (em apps/blu_v3/src/pages/app/EstrategiaRoom.tsx)
    usa 4 tabs no topo (decisoes, analises, historico, config) e NÃO possui
    aba 'documentos' nem integração com documentos/modelos.

    Estado atual (BEFORE):
        - type Tab = 'decisoes' | 'analises' | 'historico' | 'config'
        - tabs renderizadas via {(['decisoes', 'analises', 'historico', 'config'] as Tab[]).map(...)}
        - const [tab, setTab] = useState<Tab>('decisoes')
        - Nenhum import de '../../api/documents' (fetchRecentDocuments, etc.)
        - Nenhum import de '../../components/shared/EditorOverlay'
        - Nenhuma referência a 'documentos' (aba, seção, lista unificada)

    Estado esperado (AFTER — GREEN):
        - type Tab inclui 'documentos'
        - Import de fetchRecentDocuments, fetchDraftDocuments, fetchDocTemplates
        - Import de EditorOverlay e uso no JSX
        - Lista unificada (ativos + rascunhos + modelos) renderizada na aba
        - Botão "Novo Documento" aciona createDocument
        - Botão "Publicar" aciona publishDocument / saveDocument
        - Seleção de template preenche o editor

AC (Acceptance Criteria):
    AC#1 — Aba Documentos exibe lista unificada de ativos + rascunhos + modelos
           (Tab type 'documentos', fetchRecentDocuments, fetchDraftDocuments,
            fetchDocTemplates)
    AC#2 — Criar documento do zero (createDocument + botão Novo Documento)
    AC#3 — Usar template/modelo existente preenche o editor (fetchDocTemplates +
           preenchimento do editor)
    AC#4 — Edição inline (EditorOverlay importado E usado no JSX)
    AC#5 — Criar rascunho → publicar fluxo completo (publishDocument, saveDocument,
           botão Publicar)

Estado atual: RED — todas as ACs violadas porque o código atual usa tabs
decisoes/analises/historico/config, não importa nada de documents nem EditorOverlay,
e não possui aba 'documentos'. Cada teste falha com pytest.fail() detalhado em pt-BR.

Anti-Goals:
    1. NÃO usar mocks, Supabase, browser testing — só source-inspection.
    2. NÃO modificar produção — só escrever testes que comprovam o gap.
    3. NÃO remover funcionalidade existente (decisoes/analises/historico/config).
    4. NÃO introduzir dependências externas de UI (bibliotecas de editor).
"""

import re
from pathlib import Path

import pytest

# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

ESTRATEGIA_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "EstrategiaRoom.tsx"
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _read_source() -> str:
    """Read the current EstrategiaRoom.tsx as plain text."""
    if not ESTRATEGIA_ROOM_PATH.is_file():
        pytest.fail(
            f"Arquivo não encontrado: {ESTRATEGIA_ROOM_PATH}\n"
            "O teste espera que EstrategiaRoom.tsx exista."
        )
    return ESTRATEGIA_ROOM_PATH.read_text(encoding="utf-8")


# ── Tests ─────────────────────────────────────────────────────────────────


def test_ac1_documentos_exibe_lista_unificada():
    """AC#1 — Aba Documentos exibe lista unificada de ativos + rascunhos + modelos.

    RED: O código atual declara Tab = 'decisoes' | 'analises' | 'historico' | 'config'
    e não importa nenhuma função de '../../api/documents'. O esperado é que exista
    uma aba 'documentos' com type estendido e que as 3 funções de listagem
    (fetchRecentDocuments, fetchDraftDocuments, fetchDocTemplates) sejam importadas.
    """
    source = _read_source()

    # 1) O tipo Tab precisa incluir 'documentos'
    tab_type_match = re.search(r"type\s+Tab\s*=\s*([^\n]+)", source)
    tab_type_decl = tab_type_match.group(1) if tab_type_match else ""
    tab_inclui_documentos = "'documentos'" in tab_type_decl or '"documentos"' in tab_type_decl

    # 2) As 3 funções de listagem de documentos precisam ser importadas
    tem_import_recentes = "fetchRecentDocuments" in source
    tem_import_rascunhos = "fetchDraftDocuments" in source
    tem_import_templates = "fetchDocTemplates" in source

    # 3) Alguma das 3 funções precisa ser efetivamente chamada (não só importada)
    chama_recentes = bool(re.search(r"fetchRecentDocuments\s*\(", source))
    chama_rascunhos = bool(re.search(r"fetchDraftDocuments\s*\(", source))
    chama_templates = bool(re.search(r"fetchDocTemplates\s*\(", source))

    if not tab_inclui_documentos:
        pytest.fail(
            "AC#1 não atendida — Aba 'documentos' não existe no tipo Tab.\n\n"
            "O tipo Tab atual é:\n"
            "  type Tab = 'decisoes' | 'analises' | 'historico' | 'config'\n\n"
            "O esperado é que o tipo seja estendido para incluir 'documentos':\n"
            "  type Tab = 'decisoes' | 'analises' | 'historico' | 'config' "
            "| 'documentos'\n\n"
            "E que a lista de tabs renderizadas inclua 'documentos' como uma das\n"
            "opções do array usado em .map(...).\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not (tem_import_recentes and tem_import_rascunhos and tem_import_templates):
        faltando = []
        if not tem_import_recentes:
            faltando.append("fetchRecentDocuments (ativos)")
        if not tem_import_rascunhos:
            faltando.append("fetchDraftDocuments (rascunhos)")
        if not tem_import_templates:
            faltando.append("fetchDocTemplates (templates/modelos)")
        pytest.fail(
            "AC#1 não atendida — Imports de listagem de documentos incompletos.\n\n"
            "Esperado: import { fetchRecentDocuments, fetchDraftDocuments, "
            "fetchDocTemplates } from '../../api/documents'.\n\n"
            "Faltando:\n"
            + "\n".join(f"  - {fn}" for fn in faltando)
            + "\n\n"
            "A aba Documentos deve unificar três listas em uma única view:\n"
            "  - Ativos (fetchRecentDocuments): documentos publicados/recém-editados\n"
            "  - Rascunhos (fetchDraftDocuments): documentos em status='draft'\n"
            "  - Templates/Modelos (fetchDocTemplates): modelos do sistema e do cliente\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not (chama_recentes or chama_rascunhos or chama_templates):
        pytest.fail(
            "AC#1 não atendida — Funções de listagem importadas mas nunca chamadas.\n\n"
            "Os imports existem no topo do arquivo, mas nenhuma das funções\n"
            "(fetchRecentDocuments, fetchDraftDocuments, fetchDocTemplates) é\n"
            "invocada no corpo do componente EstrategiaRoom.\n\n"
            "O esperado é que sejam usadas via useQueries ou useEffect para popular\n"
            "a lista unificada da aba 'documentos'.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )


def test_ac2_criar_documento_do_zero():
    """AC#2 — Criar documento do zero (createDocument + botão Novo Documento).

    RED: O código atual não importa createDocument de '../../api/documents' nem
    possui um botão 'Novo Documento' (ou similar) que acione a criação. O esperado
    é que exista um botão visível na aba documentos que invoque createDocument.
    """
    source = _read_source()

    # 1) createDocument precisa ser importado
    tem_import_create = "createDocument" in source

    # 2) createDocument precisa ser chamado em algum lugar (provavelmente em uma
    #    mutation do react-query ou em um handler onClick)
    chama_create = bool(re.search(r"createDocument\s*\(", source))

    # 3) Deve existir um botão com label "Novo Documento" (ou variação aceitável)
    botao_novo_doc = bool(re.search(
        r"(?i)(Novo\s+Documento|Criar\s+Documento|\+?\s*Documento|novodoc|newdoc|novoDocumento)",
        source,
    ))

    if not tem_import_create:
        pytest.fail(
            "AC#2 não atendida — createDocument não está importado.\n\n"
            "O esperado é que o arquivo importe createDocument de "
            "'../../api/documents':\n\n"
            "  import {\n"
            "    fetchRecentDocuments,\n"
            "    fetchDraftDocuments,\n"
            "    fetchDocTemplates,\n"
            "    createDocument,\n"
            "    ...\n"
            "  } from '../../api/documents'\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not chama_create:
        pytest.fail(
            "AC#2 não atendida — createDocument importado mas nunca invocado.\n\n"
            "Esperado: a função deve ser chamada dentro de um useMutation ou\n"
            "handler onClick para criar um documento novo a partir do botão\n"
            "'Novo Documento'.\n\n"
            "Exemplo de uso esperado:\n"
            "  const createMut = useMutation({\n"
            "    mutationFn: (title: string) => createDocument(clientId, title),\n"
            "    onSuccess: (doc) => { ... }\n"
            "  })\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not botao_novo_doc:
        pytest.fail(
            "AC#2 não atendida — Botão 'Novo Documento' não encontrado no JSX.\n\n"
            "O esperado é que exista um botão visível ao usuário com texto\n"
            "'Novo Documento' (ou variação: 'Criar Documento', '+ Documento')\n"
            "que acione a criação via createDocument.\n\n"
            "O botão deve estar posicionado preferencialmente no cabeçalho da\n"
            "aba 'documentos' ou na barra superior da seção de Documentos.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )


def test_ac3_template_preenche_editor():
    """AC#3 — Usar template/modelo existente preenche o editor.

    RED: O código atual não importa fetchDocTemplates de documents.ts nem
    possui lógica que preencha o editor a partir de um template selecionado.
    O esperado é que a seleção de um template/modelo carregue seu conteúdo
    no EditorOverlay.
    """
    source = _read_source()

    # 1) fetchDocTemplates precisa estar importado (verificado também em AC#1)
    tem_import_templates = "fetchDocTemplates" in source
    chama_fetch_templates = bool(re.search(r"fetchDocTemplates\s*\(", source))

    # 2) Deve haver evidência de que templates são usados para preencher o editor.
    #    Procuramos por padrões como:
    #    - setEditorContent com referência a template
    #    - uso de tpl.content / template.content / editorContent
    #    - onClick de template que seta o conteúdo do editor
    preenche_de_template = bool(re.search(
        r"(?i)(template|tpl|modelo|model).*?(content|conteudo|editor|setEditor|setText|setDoc|setBody|setConteudo)",
        source,
    )) or bool(re.search(
        r"(?i)(setEditor|setText|setDoc|setBody|setConteudo|onChange|onSelect).*?(template|tpl|modelo|model)",
        source,
    ))

    # 3) Lista de templates precisa ser renderizada no JSX (não só importada)
    renderiza_templates = bool(re.search(
        r"\.map\s*\([^)]*templates",
        source,
    )) or "templates.map" in source or "DocTemplate" in source or "docTemplate" in source

    if not tem_import_templates:
        pytest.fail(
            "AC#3 não atendida — fetchDocTemplates não está importado.\n\n"
            "Sem fetchDocTemplates não é possível carregar a lista de modelos\n"
            "do sistema e do cliente para oferecer ao usuário.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not chama_fetch_templates:
        pytest.fail(
            "AC#3 não atendida — fetchDocTemplates importado mas nunca chamado.\n\n"
            "A função precisa ser invocada (via useQueries, useEffect ou similar)\n"
            "para popular a lista de templates/modelos exibida ao usuário.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not (preenche_de_template or renderiza_templates):
        pytest.fail(
            "AC#3 não atendida — Templates listados mas não preenchem o editor.\n\n"
            "fetchDocTemplates é chamado, mas não há evidência de que:\n"
            "  1. A lista de templates seja renderizada no JSX (.map(...))\n"
            "  2. A seleção de um template preencha o conteúdo do editor\n"
            "     (EditorOverlay / setText / setEditorContent)\n\n"
            "Comportamento esperado:\n"
            "  1. Listar templates do sistema e do cliente em uma coluna/seção\n"
            "  2. Ao clicar em um template, abrir o EditorOverlay com o conteúdo\n"
            "     inicial sendo template.content (ou template.editor_content)\n"
            "  3. Permitir edição e publicação a partir do template\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )


def test_ac4_editor_overlay_integrado():
    """AC#4 — Edição inline (EditorOverlay importado E usado no JSX).

    RED: O código atual não importa EditorOverlay de
    '../../components/shared/EditorOverlay' nem o renderiza no JSX.
    O esperado é que o componente seja importado E instanciado com as
    props open, docName e onClose.
    """
    source = _read_source()

    # 1) EditorOverlay precisa ser importado
    tem_import_overlay = bool(re.search(
        r"import\s+.*?EditorOverlay.*?from\s+['\"].*?EditorOverlay['\"]",
        source,
    ))

    # 2) EditorOverlay precisa ser usado no JSX (<EditorOverlay ...)
    usa_overlay_no_jsx = bool(re.search(
        r"<\s*EditorOverlay\b",
        source,
    ))

    # 3) Props esperadas: open, docName, onClose
    usa_prop_open = bool(re.search(
        r"<\s*EditorOverlay[^>]*\bopen\s*=",
        source,
    ))
    usa_prop_docname = bool(re.search(
        r"<\s*EditorOverlay[^>]*\bdocName\s*=",
        source,
    ))
    usa_prop_onclose = bool(re.search(
        r"<\s*EditorOverlay[^>]*\bonClose\s*=",
        source,
    ))

    if not tem_import_overlay:
        pytest.fail(
            "AC#4 não atendida — EditorOverlay não está importado.\n\n"
            "O componente existe em:\n"
            "  apps/blu_v3/src/components/shared/EditorOverlay.tsx\n\n"
            "Props esperadas: { open, docName, onClose }\n\n"
            "O esperado é que EstrategiaRoom.tsx importe o overlay:\n"
            "  import EditorOverlay from "
            "'../../components/shared/EditorOverlay'\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not usa_overlay_no_jsx:
        pytest.fail(
            "AC#4 não atendida — EditorOverlay importado mas não renderizado.\n\n"
            "O import existe no topo do arquivo, mas o componente não é\n"
            "instanciado no JSX. Sem renderização, a edição inline não aparece\n"
            "para o usuário.\n\n"
            "O esperado é que <EditorOverlay open={...} docName={...} "
            "onClose={...} />\n"
            "esteja presente no retorno do componente EstrategiaRoom.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not (usa_prop_open and usa_prop_docname and usa_prop_onclose):
        props_faltando = []
        if not usa_prop_open:
            props_faltando.append("open")
        if not usa_prop_docname:
            props_faltando.append("docName")
        if not usa_prop_onclose:
            props_faltando.append("onClose")
        pytest.fail(
            "AC#4 não atendida — EditorOverlay renderizado sem props obrigatórias.\n\n"
            "A interface EditorOverlayProps exige 3 props:\n"
            "  - open: boolean (controla visibilidade)\n"
            "  - docName: string (título exibido na topbar)\n"
            "  - onClose: () => void (callback de fechamento)\n\n"
            "Faltando no JSX:\n"
            + "\n".join(f"  - {p}" for p in props_faltando)
            + "\n\n"
            "Exemplo esperado:\n"
            "  <EditorOverlay\n"
            "    open={editorOpen}\n"
            "    docName={currentDoc?.title ?? 'Sem título'}\n"
            "    onClose={() => setEditorOpen(false)}\n"
            "  />\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )


def test_ac5_fluxo_rascunho_publicar():
    """AC#5 — Criar rascunho → publicar fluxo completo.

    RED: O código atual não importa saveDocument nem publishDocument de
    '../../api/documents' nem possui um botão 'Publicar' (ou similar).
    O esperado é que existam ambas as funções importadas e um botão que
    publique o documento atual, salvando o rascunho antes.
    """
    source = _read_source()

    # 1) saveDocument precisa estar importado E chamado
    tem_import_save = "saveDocument" in source
    chama_save = bool(re.search(r"saveDocument\s*\(", source))

    # 2) publishDocument precisa estar importado E chamado
    tem_import_publish = "publishDocument" in source
    chama_publish = bool(re.search(r"publishDocument\s*\(", source))

    # 3) Deve existir um botão "Publicar" no JSX
    botao_publicar = bool(re.search(
        r"(?i)(Publicar|Publish|publicarDoc|publishDoc|onPublish|handlePublish)",
        source,
    ))

    if not (tem_import_save and tem_import_publish):
        pytest.fail(
            "AC#5 não atendida — Funções de save/publish não estão importadas.\n\n"
            "O fluxo rascunho → publicar precisa de ambas:\n"
            "  - saveDocument(id, clientId, content): persiste o rascunho\n"
            "  - publishDocument(id, clientId): marca como publicado\n\n"
            "Esperado em EstrategiaRoom.tsx:\n"
            "  import {\n"
            "    saveDocument,\n"
            "    publishDocument,\n"
            "    ...\n"
            "  } from '../../api/documents'\n\n"
            "Faltando:\n"
            + (
                "  - saveDocument (salvar rascunho)\n" if not tem_import_save else ""
            )
            + (
                "  - publishDocument (publicar)\n" if not tem_import_publish else ""
            )
            + "\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not (chama_save and chama_publish):
        pytest.fail(
            "AC#5 não atendida — Funções de save/publish importadas mas nunca "
            "chamadas.\n\n"
            "Esperado: ambas devem ser usadas em useMutation ou handlers onClick.\n"
            "Exemplo:\n"
            "  const saveMut = useMutation({\n"
            "    mutationFn: ({id, content}) => saveDocument(id, clientId, content),\n"
            "    onSuccess: () => addToast('ok', 'Salvo', 'Rascunho salvo.')\n"
            "  })\n\n"
            "  const publishMut = useMutation({\n"
            "    mutationFn: (id) => publishDocument(id, clientId),\n"
            "    onSuccess: () => addToast('ok', 'Publicado', 'Documento publicado.')\n"
            "  })\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not botao_publicar:
        pytest.fail(
            "AC#5 não atendida — Botão 'Publicar' não encontrado no JSX.\n\n"
            "O esperado é que exista um botão visível (no EditorOverlay ou na\n"
            "própria aba documentos) com texto 'Publicar' (ou variação\n"
            "aceitável: 'Publish', 'handlePublish') que acione publishDocument.\n\n"
            "Fluxo completo esperado:\n"
            "  1. Usuário edita conteúdo do documento\n"
            "  2. Clica em 'Salvar rascunho' → saveDocument(content)\n"
            "  3. Clica em 'Publicar' → publishDocument(id)\n"
            "  4. Documento muda de status 'draft' para 'published'\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )


def test_ac6_legado_agent_slug_documentos():
    """AC#6 — Documentos do agent_slug 'documentos' (legado) ainda aparecem.

    RED: O EstrategiaRoom.tsx atual não importa nada de '../../api/documents'
    e não contém nenhuma referência a agent_slug que inclua 'documentos'. A
    query de listagem (fetchRecentDocuments / fetchDraftDocuments) hoje filtra
    apenas 'estrategia' (ou o agente da room), o que faz com que documentos
    antigos salvos com agent_slug='documentos' (legado) desapareçam da nova
    aba Documentos unificada.

    GREEN esperado: durante a transição da aba Documentos, a query (no próprio
    EstrategiaRoom.tsx ou via constants/queries importados) precisa incluir
    AMBOS os agent_slugs:

        agent_slug IN ('documentos', 'estrategia')

    Aceita qualquer uma das formas equivalentes (array, IN, constantes,
    imports de api/documents etc.) desde que ambos os slugs coexistam na
    mesma expressão de filtro.
    """
    source = _read_source()

    # 1) Tem que existir alguma menção a 'documentos' como agent_slug no arquivo
    #    (string literal 'documentos' ou "documentos").
    tem_slug_documentos = bool(re.search(
        r"['\"]documentos['\"]",
        source,
    ))

    # 2) Tem que existir alguma menção a 'estrategia' como agent_slug.
    tem_slug_estrategia = bool(re.search(
        r"['\"]estrategia['\"]",
        source,
    ))

    # 3) Tem que existir um token 'agent_slug' (ou 'agent_slugs') no arquivo —
    #    a string sozinha não basta, pois pode aparecer em UI/rotação/etc.
    tem_token_agent_slug = bool(re.search(
        r"\bagent_slug[s]?\b",
        source,
    ))

    # 4) Os DOIS slugs precisam estar juntos na mesma expressão/linha/bloco
    #    referenciando agent_slug. Procuramos padrões como:
    #      agent_slug IN ('documentos', 'estrategia')
    #      agent_slug: ['documentos', 'estrategia']
    #      agent_slugs = ['documentos', 'estrategia']
    #    Aceitando qualquer ordem (documentos antes OU depois de estrategia).
    filtro_unificado = bool(re.search(
        r"\bagent_slug[s]?\b[^;\n]*['\"]documentos['\"][^;\n]*['\"]estrategia['\"]",
        source,
    )) or bool(re.search(
        r"\bagent_slug[s]?\b[^;\n]*['\"]estrategia['\"][^;\n]*['\"]documentos['\"]",
        source,
    ))

    if not tem_token_agent_slug:
        pytest.fail(
            "AC#6 não atendida — O termo 'agent_slug' não aparece em "
            "EstrategiaRoom.tsx.\n\n"
            "Durante a unificação da aba Documentos, a query precisa ser\n"
            "construída em EstrategiaRoom.tsx (ou via constants/queries\n"
            "importados) referenciando agent_slug para filtrar 'documentos'\n"
            "e 'estrategia' em conjunto.\n\n"
            "Hoje o componente não importa nada de '../../api/documents' e\n"
            "não menciona agent_slug, então a aba unificada não tem como\n"
            "incluir os documentos do agent legado 'documentos'.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not tem_slug_documentos:
        pytest.fail(
            "AC#6 não atendida — agent_slug 'documentos' (legado) não é "
            "mencionado em EstrategiaRoom.tsx.\n\n"
            "Documentos antigos foram salvos com agent_slug='documentos'\n"
            "(antes da unificação). Para que continuem aparecendo na nova\n"
            "aba Documentos, a query precisa incluir explicitamente o slug\n"
            "legado junto com 'estrategia'.\n\n"
            "Exemplos de uso esperado:\n"
            "  .in('agent_slug', ['documentos', 'estrategia'])\n"
            "  agent_slug IN ('documentos', 'estrategia')\n"
            "  const DOC_AGENT_SLUGS = ['documentos', 'estrategia']\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not tem_slug_estrategia:
        pytest.fail(
            "AC#6 não atendida — agent_slug 'estrategia' não é mencionado "
            "em EstrategiaRoom.tsx.\n\n"
            "A unificação precisa manter os documentos do agent 'estrategia'\n"
            "juntos com os legados de 'documentos'. Sem 'estrategia' no\n"
            "filtro, a nova aba perderia os documentos do próprio agente\n"
            "estratégia.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    if not filtro_unificado:
        pytest.fail(
            "AC#6 não atendida — Os agent_slugs 'documentos' e 'estrategia' "
            "aparecem no arquivo, mas NÃO estão juntos na mesma expressão\n"
            "de filtro de agent_slug.\n\n"
            "Para a transição funcionar, ambos precisam coexistir em um\n"
            "único filtro (IN, array, constante) referenciando agent_slug.\n\n"
            "Padrões aceitos (qualquer ordem):\n"
            "  .in('agent_slug', ['documentos', 'estrategia'])\n"
            "  .in('agent_slug', ['estrategia', 'documentos'])\n"
            "  agent_slug IN ('documentos', 'estrategia')\n"
            "  const DOC_AGENT_SLUGS = ['documentos', 'estrategia']\n"
            "  const DOC_AGENT_SLUGS = ['estrategia', 'documentos']\n\n"
            "Sem o filtro conjunto, a aba unificada ou mostra apenas o\n"
            "legado OU apenas os documentos do agent estratégia — nunca os\n"
            "dois ao mesmo tempo.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )
