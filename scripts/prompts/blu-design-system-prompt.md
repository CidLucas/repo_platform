# Blu Design System — Artefatos & Templates de Documentos

## Objetivo
Gerar templates HTML completos que definam a linguagem visual da plataforma Blu para todos os artefatos que um SMB brasileiro consome no dia a dia. Cada template deve ser HTML auto-contido usando os design tokens do Blu e servir como guia para produção de documentos reais, charts, cards, tabelas e elementos de chat.

## Design Tokens (CSS Variables)
```css
/* Cores */
--bg:    #03071C;        /* fundo escuro */
--glass: rgba(255,255,255,0.065);  /* superficie painel */
--gl2:   rgba(255,255,255,0.07);
--gb:    rgba(255,255,255,0.10);   /* borda sutil */
--gb2:   rgba(255,255,255,0.20);   /* borda hover */
--fg:    #DFE3EE;        /* texto primario */
--mu:    rgba(223,227,238,0.42);   /* texto muted */
--mu2:   rgba(223,227,238,0.64);   /* texto secundario */
--ac:    #8C5FDB;        /* roxo Blu - accent primario */
--adim:  rgba(140,95,219,0.15);
--urg:   #EF4444;        /* vermelho - urgente/perigo */
--udim:  rgba(239,68,68,0.13);
--att:   #F59E0B;        /* ambar - atencao */
--adm2:  rgba(245,158,11,0.13);
--ok:    #10B981;        /* verde - sucesso */
--odim:  rgba(16,185,129,0.13);
--r:     8px;            /* border-radius padrao */
--rl:    12px;           /* border-radius grande */
--rxl:   20px;           /* border-radius extra (mobile sheets) */
--body:  'Inter', -apple-system, system-ui, sans-serif;
--mono:  'JetBrains Mono', 'SF Mono', ui-monospace, monospace;

/* Sombras */
--shadow-1: 0 2px 14px rgba(0,0,0,.28);          /* paineis em repouso */
--shadow-2: 0 4px 22px rgba(0,0,0,.36);          /* paineis hover */
--shadow-3: 0 12px 40px rgba(0,0,0,.6);          /* modais/popovers */

/* Light theme (body.light) */
--bg:    #F0EEE8;  --fg:    #111827;  --ac:    #6D28D9;
--mu:    rgba(17,24,39,0.42);  --mu2:   rgba(17,24,39,0.62);
--glass: rgba(255,255,255,0.55);  --gb: rgba(0,0,0,0.09);
```

## Cores dos Agentes (por Sala)
| Sala | Slug | Cor |
|------|------|-----|
| Compras | compras | #818cf8 indigo |
| Financeiro | financeiro | #34d399 green |
| Agenda | agenda | #fb923c orange |
| Estrategia | estrategia | #a78bfa violet |
| Clientes | clientes | #f472b6 pink |
| Biblioteca | biblioteca | #818cf8 |

## Icones (Phosphor Icons CDN)
```html
<link rel="stylesheet" href="https://unpkg.com/@phosphor-icons/web@2.1.1/src/regular/style.css">
<!-- Uso: <i class="ph ph-house"></i> -->
```
| Sala | Icone |
|------|-------|
| Home | ph-house |
| Compras | ph-shopping-cart |
| Financeiro | ph-chart-bar |
| Agenda | ph-calendar-dots |
| Estrategia | ph-target |
| Clientes | ph-users-three |
| Biblioteca | ph-books |
| Atividade | ph-bell |

## Diretrizes de Estilo

### Tipografia
- Body: `--body` (Inter). Mono: `--mono` (JetBrains Mono) para numeros, timestamps, IDs, moedas
- Base: 13px, line-height 1.5
- Headlines: tracking negativo (-1px a -2px), weight 800
- Labels: 11px / 700 / uppercase / .1em tracking / `var(--ac)`
- Headers de painel: 9.5-10px / 700 / uppercase / .08em tracking / muted
- Logo: Nunito 900 (apenas para o wordmark "blu")

### Glassmorphism
Todos os paineis usam:
```css
background: var(--glass);
backdrop-filter: blur(16px);
border: 1px solid var(--gb);
box-shadow: var(--shadow-1), inset 0 0 0 1px rgba(255,255,255,.05);
```

### Cantos
- `--r` (8px): botoes, inputs, cards
- `--rl` (12px): paineis, chips, modais
- `--rxl` (20px): bottom sheets mobile

### Animacao
- Transicoes: ease-out, nunca ease-in
- Hover: 0.10s (rapido)
- Fade-in: @keyframes fi (opacity 0->1, 0.15s)
- Toast: @keyframes ts (translateX + opacity, 0.16s)
- Expandir/recolher: max-height 0.20s

### Icones de acao (uso no UI, sem emoji)
- Aprovacao: <i class="ph ph-check-circle"></i>
- Rejeicao: <i class="ph ph-x-circle"></i>
- Urgente: <i class="ph ph-lightning"></i>
- Documento: <i class="ph ph-file-text"></i>
- Download: <i class="ph ph-download-simple"></i>
- Assinar: <i class="ph ph-signature"></i>
- Salvar: <i class="ph ph-floppy-disk"></i>
- Adiar: <i class="ph ph-clock-clockwise"></i>
- Insight: <i class="ph ph-lightbulb"></i>
- Alerta: <i class="ph ph-warning"></i>
- Buscar: <i class="ph ph-magnifying-glass"></i>
- Fechar: <i class="ph ph-x"></i>
- Menu: <i class="ph ph-dots-three-vertical"></i>
- Anexo: <i class="ph ph-paperclip"></i>
- Calendario: <i class="ph ph-calendar"></i>

## Artefatos para Gerar (um HTML por secao)

### 1. Charts (`charts.html`)
Charts SVG sem dependencias externas:
- **Line chart** — MRR 12 meses com area gradient, pontos, grid
- **Bar chart** — Receita mensal por categoria
- **Horizontal bar** — Top 5 clientes
- **Donut chart** — Breakdown de despesas com legenda
- **Area chart** — Crescimento acumulado
- **Sparkline** — Mini chart inline para KPIs
- **Gauge** — NPS com faixas de cor

Cada chart deve ter: titulo + subtitulo, eixos formatados (R$, %, unidades), tooltip hover com valor exato + data, legenda, largura responsiva.

Paleta: `--ac` (#8C5CF6), `--ok` (#10B981), #3B82F6, `--att` (#F59E0B), `--urg` (#EF4444), #EC4899, #14B8A6, #8B5CF6.

### 2. Tabelas (`tables.html`)
Tabelas HTML estilizadas:
- Tabela financeira (Descricao, Valor, % Total, Variacao MoM) com totalizador no footer
- Tabela KPIs (Nome, Mes atual, Mes anterior, Meta, Status)
- Lista de clientes (Empresa, Receita, Plano, Status)
- Budget vs Real (Categoria, Budget, Real, Variacao %) com cores condicionais
- Com sticky header, linhas alternadas, hover, badges de status, alinhamento numerico (mono font), paginacao

### 3. Documentos Financeiros (`financial-docs.html`)
Documentos formatados para visualizacao na tela escura E para exportacao:
- **Fechamento mensal** — Sumario executivo > Receitas > Despesas > P&L > KPIs > Notas
- **Fluxo de caixa** — Operacional > Investimento > Financiamento > Saldo
- **Proposta de orcamento** — Departamentos, YoY, assinaturas
- **Invoice** — Logo, dados cliente, itens, totais, codigo de barras
- **Proposta comercial** — Capa > Escopo > Precificacao > Termos > Assinatura
- **Relatorio de despesas** — Data, categoria, valor, status do recibo
- **Balanco patrimonial** — Ativos, Passivos, Patrimonio liquido

### 4. Documentos Estrategicos (`strategy-docs.html`)
- **Plano estrategico** — Visao > Missao > Objetivos > Iniciativas > KPIs > Timeline
- **OKR** — Objective > Key Results (progress bars) > Owner
- **Relatorio de contexto** — Sumario executivo > Analise > Recomendacoes
- **Ata de reuniao** — Data, participantes, pauta, discussoes, acoes (dono + prazo)
- **SWOT** — Grid 2x2 forcas/fraquezas/oportunidades/ameacas
- **Plano de acao** — Prioridade, Acao, Responsavel, Prazo, Status

### 5. Elementos de Chat (`chat-elements.html`)
- Bolha de mensagem (usuario: direita, accent bg; agente: esquerda, glass bg)
- Card estruturado inline no chat — dados com label + valor
- Tabela interativa colapsavel no chat
- Acoes rapidas — chips de resposta sugerida
- Loading — animacao de digitacao do agente (3 dots pulsando)
- Preview de documento no chat (thumbnail com icone + nome)
- Aprovacao inline no chat (botoes aprovar/rejeitar)
- Chart miniatura no chat
- Upload drag & drop (area tracejada com icone de upload)

### 6. Cards & Kanban (`cards-kanban.html`)
- **Card de ativacao de rotina** — nome + passos numerados + botoes aprovar/rejeitar
- **Card de decisao** — label do agente + badge de prioridade + corpo expansivel + botoes de acao
- **KPI card** — label + valor atual + delta (positivo/negativo) + sparkline
- **Card de documento** — icone do tipo (MD, DOC, PDF) + nome + pasta + data + status
- **Card de cliente** — avatar (iniciais) + nome + receita + plano + indicador de status
- **Card de tarefa** — checkbox + titulo + data de vencimento + responsavel
- **Kanban** — 3-4 colunas (A fazer / Fazendo / Revisao / Pronto) com card drag visual

### 7. Formularios (`forms-inputs.html`)
Inputs dark theme: text, textarea, select, checkbox customizado, radio, toggle, date, search, file upload.
Button variants: `bp` (primario), `bs` (secundario), `bg` (ghost), `brd` (danger).
Todos os estados: default, hover, active, disabled, loading (com spinner).

### 8. Navegacao & Shell (`navigation-shell.html`)
- Topbar (logo + breadcrumb + search + notificacoes + avatar)
- Sidebar (icones + tooltips + indicador ativo + badge de notificacao)
- Room grid (painel principal 2/3 + coluna direita 1/3 + bottom strip)
- Panel com header + tabs + body + analytics footer
- Bottom strip com 3 insight cards
- Loading skeletons (shimmer animation)
- Empty states (icone + mensagem centralizada)

## Document Export Mode — Aparencia Seria para Documentos Emitidos

Quando um documento e exportado / gerado para download ou impressao (PDF, HTML para impressao), ele deve usar um **modo serio** com aparencia de documento corporativo tradicional:

### Regras do Modo Exportacao
1. **Background**: Branco puro (#FFFFFF). Sem glassmorphism, sem backdrop-filter, sem gradientes.
2. **Texto**: Preto (#000000) ou cinza escuro (#333333) para corpo. Nunca usar as cores do tema escuro.
3. **Cores de destaque**: Usar apenas preto, cinza, e opcionalmente um tom de azul escuro (#1a237e) para headers e acentos sutis. Sem roxo, sem verde, sem vermelho.
4. **Fontes**: Inter para corpo, JetBrains Mono para numeros. Tamanhos: 11pt para corpo, 14pt para headers de secao, 18pt para titulo do documento.
5. **Bordas**: 1px solid #ccc ou #ddd. Sem cantos arredondados (border-radius: 0).
6. **Tabelas**: Bordas completas (todas as celulas com borda). Header com fundo cinza claro (#f5f5f5).
7. **Sem sombras**: Nenhum box-shadow.
8. **Sem backdrop-filter**: Nenhum efeito de vidro.
9. **Margens**: 2cm nas laterais, espacamento adequado para impressao A4.
10. **Logo**: Versao monocromatica do logo Blu (preto ou cinza escuro).
11. **Numero de pagina**: No footer, centralizado.
12. **Assinaturas**: Linhas tradicionais com "________________________" e nome + cargo abaixo.

### Como implementar
Adicionar uma classe `.export-mode` ou usar `@media print`:
```css
.export-mode, @media print {
  --bg: #FFFFFF !important;
  --fg: #000000 !important;
  --mu: #666666 !important;
  --mu2: #333333 !important;
  --ac: #1a237e !important;
  --glass: #FFFFFF !important;
  --gb: #ddd !important;
  --gb2: #bbb !important;
  --shadow-1: none !important;
  --shadow-2: none !important;
  --shadow-3: none !important;
}
```

Cada template de documento deve vir com um botao "Exportar / Baixar" que aplica `.export-mode` e abre a impressao do navegador.

## Diretrizes de Conteudo
- **Idioma**: Portugues brasileiro. Todo copy em pt-BR.
- **Tom**: Direto, confiante. "Voce" (informal), nunca "nos".
- **CTAs**: Verbo na frente: "Aprovar", "Criar documento", "Salvar"
- **Labels**: ALL CAPS com text-transform: uppercase
- **Badges**: all caps, weight 700
- **Botoes**: Sentence case
- **Emojis**: Nao usar emojis em nenhum elemento de UI. Substituir por icones Phosphor ou texto.

## Estilo Visual (modo app escuro)
- Background gradient: radiais suaves (azul top-left, indigo bottom-right)
- Nenhuma imagem, foto ou ilustracao no app — apenas UI tokenizada
- Scrollbars: 3-6px, thumb `--gb2`, track transparent
- Hover em rows: `rgba(255,255,255,.04)`
- KPI cells: `background: rgba(0,0,0,.25)`

## Output
Cada arquivo HTML completo com:
- `<style>` com todas as CSS variables + classes necessarias
- `<body>` com o template
- Phosphor Icons CDN para icones
- SVG inline para charts
- Zero dependencias externas alem do CDN de icones
- Classes seguindo padrao BEM-like do Blu (ex: `.kpi-cell`, `.dc-row`, `.ich`, `.anl-card`)
- Botaozinho "Exportar / Baixar" no topo de cada template de documento
- CSS `@media print` com o modo serio branco-e-preto
