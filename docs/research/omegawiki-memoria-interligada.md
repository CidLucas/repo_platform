# OmegaWiki como Memória Interligada Crescente para Agentes de IA

> Análise do repositório [skyllwt/OmegaWiki](https://github.com/skyllwt/OmegaWiki)  
> Implementação da visão LLM-Wiki de Andrej Karpathy (DAIR Lab, Universidade de Pequim)

---

## 1. Como o OmegaWiki Funciona

### Origem: A Visão de Karpathy

O OmegaWiki nasce de uma ideia de Andrej Karpathy chamada **LLM-Wiki**: em vez de usar um LLM para responder perguntas de forma descartável (como no RAG tradicional), o modelo deveria **construir e manter uma wiki persistente e estruturada** a partir de fontes de conhecimento. Cada novo documento ingerido não apenas gera uma resposta — ele enriquece permanentemente uma base de conhecimento que cresce e se interliga ao longo do tempo.

### Conceito Central: O Wiki como Fonte Única da Verdade

O **wiki é o estado persistente do agente**. O LLM processa documentos *uma vez* e transcreve o conhecimento em páginas estruturadas e interligadas. A partir daí, qualquer pergunta parte desse wiki como base.

```
Documento bruto (.pdf/.tex)
        ↓  /ingest
   Páginas wiki estruturadas
        ↓  interligadas por [[wikilinks]]
   Grafo de conhecimento
        ↓  consultado por
   Qualquer skill subsequente
```

### Estrutura: 9 Tipos de Entidade

- **Paper** (`wiki/papers/`) — Resumo estruturado: problema, ideia central, método, experimentos, limitações
- **Concept** (`wiki/concepts/`) — Conceitos técnicos que aparecem em múltiplos artigos
- **Topic** (`wiki/topics/`) — Mapas de direções, SOTA, benchmarks, lacunas abertas
- **Person** (`wiki/people/`) — Perfis com áreas de atuação e trabalhos
- **Idea** (`wiki/ideas/`) — Ideias com lifecycle completo, argumento de novidade
- **Experiment** (`wiki/experiments/`) — hipótese → setup → resultados → atualização da ideia vinculada
- **Method** (`wiki/methods/`) — Técnicas reutilizáveis entre artigos
- **Summary** (`wiki/Summary/`) — Surveys de domínio cobrindo múltiplos tópicos
- **Foundation** (`wiki/foundations/`) — Conhecimento de base (páginas terminais)

### Como as Páginas se Interligam

**1. Wikilinks bidirecionais (formato Obsidian)**  
Toda página usa `[[NomeDaEntidade]]`. Esses links são bidirecionais — é possível saber quem referencia qualquer entidade.

**2. Grafo semântico tipado (`graph/edges.jsonl`)**  
Arestas com tipo explícito:
- Entre papers: `same_problem_as`, `builds_on`, `improves_on`, `challenges`, `surveys`
- Entre papers e conceitos: `introduces_concept`, `uses_concept`, `extends_concept`
- Entre experimentos e ideias: `supports`, `contradicts`, `tested_by`, `invalidates`

**3. Grafo de citações bibliográficas (`graph/citations.jsonl`)**  
Relações formais de citação entre artigos.

Esse triplo mecanismo faz o conhecimento ser **navegável por semântica, por estrutura e por proveniência** simultaneamente.

---

## 2. Como Aplicar como Camada de Memória para Agentes

### O Problema que Resolve

Agentes de IA hoje têm memória frágil. Sistemas RAG armazenam chunks vetorizados, mas esses chunks são **ilhas de texto sem contexto relacional**. Um agente que aprende algo sobre X em uma sessão não sabe, na próxima, como X se conecta a Y, que por sua vez contrasta com Z.

O OmegaWiki resolve isso tornando a memória **estruturada, relacional e persistente**.

### Arquitetura de Memória Baseada em Wiki

```
┌─────────────────────────────────────────┐
│           AGENTE DE IA                  │
│  ┌─────────┐    ┌──────────────────┐   │
│  │ Contexto│    │   Skills/Tools   │   │
│  │  Atual  │    │  (ler, escrever, │   │
│  └────┬────┘    │   conectar wiki) │   │
│       │         └────────┬─────────┘   │
└───────┼──────────────────┼─────────────┘
        ▼                  ▼
┌───────────────────────────────────────┐
│         WIKI COMO MEMÓRIA             │
│  Entidades  ←→  Grafo Semântico       │
│  (páginas)      (arestas tipadas)     │
│  • Eventos    • Pessoas               │
│  • Conceitos  • Projetos              │
│  • Decisões   • Preferências          │
└───────────────────────────────────────┘
```

### 5 Princípios para Adaptar o Conceito

1. **Ingestão como escrita de memória** — cada interação relevante vira entidade estruturada, não log bruto
2. **Lifecycle de entidades** — tarefas, decisões, hipóteses têm estados rastreados (ativa → validada → descartada)
3. **Lacunas explícitas como motor de curiosidade** — gaps conhecidos são entidades registradas que o agente resolve ativamente
4. **Experimentos fracassados como memória anti-repetição** — tentativas inválidas ficam como `status: invalidated`, servem de freio
5. **Grafo como recuperação contextual** — navegação por tipo de relação, não só similaridade vetorial

---

## 3. OmegaWiki vs RAG Vetorial Tradicional

| Dimensão | RAG Vetorial | Wiki-Centric |
|---|---|---|
| **Unidade de memória** | Chunk de texto (~500 tokens) | Página de entidade tipada com schema |
| **Relações** | Nenhuma — chunks são ilhas | Grafo de arestas tipadas e bidirecionais |
| **Persistência** | Redescoberto a cada query | Compilado uma vez, mantido para sempre |
| **Lacunas** | Invisíveis | Rastreadas explicitamente |
| **Falhas e contradições** | Perdidas | Registradas com tipo (`contradicts`, `invalidates`) |
| **Compounding** | Não — custo idêntico em cada query | Sim — cada dado enriquece o grafo inteiro |
| **Navegação** | Busca por similaridade (k-NN) | Traversal de grafo + busca semântica |
| **Transparência** | Opaca | Rastreável — cada link tem tipo e proveniência |
| **Custo por query** | Alto — reprocessa documentos | Baixo — lê páginas já processadas |

**Analogia:**
- **RAG**: biblioteca com livros empilhados — você procura por palavra-chave e lê trechos
- **Wiki**: enciclopédia com índice cruzado e mapa conceitual — você navega por significado

---

## 4. Exemplos Concretos

### Agente de Suporte ao Desenvolvedor

**Wiki do projeto:**
- `Project/backend-auth` — arquitetura do módulo de autenticação
- `Concept/jwt-refresh-token` — como o time implementou refresh tokens
- `Experiment/tentativa-redis-session` — status: `invalidated`, motivo: latência inaceitável
- `Person/ana` — prefere soluções simples, evita over-engineering
- `Concept/decisao-postgres-vs-mongo` — aresta `decided_because`

**Resultado:** quando alguém pergunta "podemos usar Redis para sessão?", o agente lê o grafo, encontra o experimento invalidado e **explica o motivo histórico** sem que ninguém precise lembrar.

### Assistente Pessoal com Memória de Longo Prazo

**Wiki pessoal:**
- `Person/usuario` — preferências, contexto profissional
- `Experiment/tentativa-academia-manha` — status: `abandoned`, motivo: conflito com reuniões
- `Idea/mudar-para-nova-cidade` — prós/contras acumulados ao longo do tempo
- `Concept/restricoes-dieteticas` — intolerâncias e preferências

**Resultado:** o agente nunca re-pergunta sobre restrições alimentares após a terceira interação. Ao retomar a discussão de mudança de cidade, apresenta análise evoluída — não recomeça do zero.

### Inteligência Competitiva Empresarial

**Wiki corporativo:**
- `Person/concorrente-X` → `Topic/estrategia-pricing-X` com arestas `announced`, `reversed`
- `Concept/feature-diferenciacao` com arestas `offered_by`, `missing_in`, `planned_by`
- `Idea/expansao-latam` com lacuna explícita: "Falta dado sobre regulação tributária no Brasil"

**Resultado:** quando novo relatório contradiz posição anterior, o agente detecta automaticamente a aresta `challenges` e apresenta a linha do tempo completa da contradição.

---

## Conclusão

O OmegaWiki representa uma mudança paradigmática: substituir "chunks recuperados por similaridade" por um **grafo de entidades tipadas e interligadas**. O resultado é um sistema que aprende de verdade — onde o conhecimento se acumula, se contradiz, se valida e se organiza de forma que qualquer agente pode navegar com precisão relacional.

A ideia central para o Blu: **memória como grafo vivo** — não um arquivo de logs, não um índice vetorial, mas uma representação estruturada do mundo que o agente conhece, com todas as relações explícitas, lacunas rastreadas e fracassos registrados como cidadãos de primeira classe.

Isso transforma agentes de sistemas *reativos* em sistemas *epistêmicos* — capazes não apenas de recuperar informação, mas de raciocinar sobre o que sabem, o que não sabem, e o que aprenderam ao longo do tempo.
