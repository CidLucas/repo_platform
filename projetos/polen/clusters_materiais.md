# Clusters de Materiais — Preço Justo de Recicláveis

## Visão Geral

A estratégia de clusterização utilizada é a de **Price Tiers** (faixas de preço por quantis), que obteve o melhor desempenho preditivo entre as 3 estratégias avaliadas — com 35% menos erro que a classificação original por tipo de polímero.

### Hierarquia de Classificação

1. **Grupo base** (`material_group`): classificação primária por tipo de polímero (PET, PP, PEAD, PS, PE/FILME, PVC, BOPP/RAFIA, OUTROS)
2. **Grupo refinado** (`material_group_refined`): subdivisão do grupo OUTROS em subgrupos (METAIS_DIVERSOS, OUTROS_PLASTICOS_MISTOS, OUTROS_RESIDUAL, etc.)
3. **Price Tiers** (`price_tier`): dentro de cada grupo refinado, os produtos são segmentados em 3 faixas de preço (TIER1 = preço baixo, TIER2 = preço médio, TIER3 = preço alto)

**Total de clusters ativos:** 24

---

## Clusters por Grupo de Material

### PET (Politereftalato de Etileno)

#### PET_TIER1 — Faixa de Preço Baixa
- **Produtos:** FITA PET VERDE, PET AZEITE, PET ÓLEO, SUCATA DE PET BANDEJA, SUCATA DE PET COLORIDO
- **Observações:** 1.309
- **Cobertura geográfica:** BA, CE, DF, ES, GO, MG, MS, PR, RJ, RS, SP
- **Nº máx. de produtos distintos por estado:** 5

#### PET_TIER2 — Faixa de Preço Média
- **Produtos:** PET COLORIDO, SUCATA DE PET LEITOSO, SUCATA PET
- **Observações:** 1.365
- **Cobertura geográfica:** AM, BA, CE, DF, ES, GO, MA, MG, PA, PR, RJ, RS, SC, SP
- **Nº máx. de produtos distintos por estado:** 3

#### PET_TIER3 — Faixa de Preço Alta
- **Produtos:** PET CRISTAL, PET VERDE, SUCATA DE PET CRISTAL, SUCATA DE PET VERDE
- **Observações:** 3.810
- **Cobertura geográfica:** BA, ES, GO, MG, MS, MT, PA, PB, PE, PR, RJ, RN, RS, SP
- **Nº máx. de produtos distintos por estado:** 4

#### PET (sem tier)
- **Produtos:** SUCATA DE PET ÂMBAR, SUCATA PET CRISTAL E VERDE
- **Observações:** 6
- **Cobertura geográfica:** RS
- **Nota:** Volume insuficiente para divisão em tiers

---

### PP (Polipropileno)

#### PP_TIER1 — Faixa de Preço Baixa
- **Produtos:** PP BALDE BACIA BRANCO, PP BALDE BACIA COLORIDO, PP PRETO, SUCATA DE PP BALDE BACIA BRANCO, SUCATA DE PP MARGARINA
- **Observações:** 1.491
- **Cobertura geográfica:** CE, DF, ES, GO, MA, MG, MS, PE, PR, RJ, RS, SP
- **Nº máx. de produtos distintos por estado:** 5

#### PP_TIER2 — Faixa de Preço Média
- **Produtos:** SUCATA DE PP MINERAL, SUCATA DE PP TAMPINHA
- **Observações:** 137
- **Cobertura geográfica:** CE, PR, RS
- **Nº máx. de produtos distintos por estado:** 2

#### PP_TIER3 — Faixa de Preço Alta
- **Produtos:** PP BRANCO, PP MARGARINA, PP MINERAL, PP NATURAL
- **Observações:** 1.870
- **Cobertura geográfica:** BA, DF, ES, GO, MG, MS, PR, RJ, RN, RS, SC, SP
- **Nº máx. de produtos distintos por estado:** 4

#### PP (sem tier)
- **Produtos:** FITA PP BRANCA, FITA PP PRETA, SUCATA DE PP BALDE BACIA COLORIDO
- **Observações:** 12
- **Cobertura geográfica:** MG, RS
- **Nota:** Volume insuficiente para divisão em tiers

---

### PEAD (Polietileno de Alta Densidade)

#### PEAD_TIER1 — Faixa de Preço Baixa
- **Produtos:** PEAD MISTO, SUCATA DE PEAD SACOLINHA
- **Observações:** 448
- **Cobertura geográfica:** BA, CE, DF, PR, SP
- **Nº máx. de produtos distintos por estado:** 2

#### PEAD_TIER2 — Faixa de Preço Média
- **Produtos:** SUCATA DE PEAD COLORIDO, SUCATA DE PEAD CRISTAL
- **Observações:** 1.823
- **Cobertura geográfica:** DF, ES, GO, MA, MG, PR, RJ, RS, SC, SP
- **Nº máx. de produtos distintos por estado:** 2

#### PEAD_TIER3 — Faixa de Preço Alta
- **Produtos:** PEAD BOMBONA, SUCATA DE PEAD BRANCO
- **Observações:** 1.368
- **Cobertura geográfica:** DF, ES, MA, MG, PA, PR, RJ, RS, SC, SP
- **Nº máx. de produtos distintos por estado:** 2

#### PEAD (sem tier)
- **Produtos:** PEAD CRISTAL
- **Observações:** 30
- **Cobertura geográfica:** ES
- **Nota:** Volume insuficiente para divisão em tiers

---

### PS (Poliestireno)

#### PS_TIER1 — Faixa de Preço Baixa
- **Produtos:** SUCATA DE PS PRETO
- **Observações:** 53
- **Cobertura geográfica:** SP
- **Nº máx. de produtos distintos por estado:** 1

#### PS_TIER2 — Faixa de Preço Média
- **Produtos:** SUCATA DE PS COPINHO
- **Observações:** 10
- **Cobertura geográfica:** PR
- **Nº máx. de produtos distintos por estado:** 1

#### PS_TIER3 — Faixa de Preço Alta
- **Produtos:** PS COPINHO
- **Observações:** 138
- **Cobertura geográfica:** MG, PR, RS, SP
- **Nº máx. de produtos distintos por estado:** 1

---

### PE/FILME (Polietileno / Filmes)

#### PE/FILME_TIER1 — Faixa de Preço Baixa
- **Produtos:** PE PRETO / PE COLORIDO
- **Observações:** 78
- **Cobertura geográfica:** DF, RS, SP
- **Nº máx. de produtos distintos por estado:** 1

#### PE/FILME_TIER2 — Faixa de Preço Média
- **Produtos:** SUCATA DE FILME COLORIDO
- **Observações:** 232
- **Cobertura geográfica:** CE, ES, MA, MG, PA, RJ, RS
- **Nº máx. de produtos distintos por estado:** 1

#### PE/FILME_TIER3 — Faixa de Preço Alta
- **Produtos:** PE CANELA
- **Observações:** 41
- **Cobertura geográfica:** PR, RS, SP
- **Nº máx. de produtos distintos por estado:** 1

#### PE/FILME (sem tier)
- **Produtos:** SUCATA DE FILME CANELA, SUCATA DE FILME PRETO
- **Observações:** 10
- **Cobertura geográfica:** RS
- **Nota:** Volume insuficiente para divisão em tiers

---

### PVC (Policloreto de Vinila)

#### PVC
- **Produtos:** SUCATA DE PVC
- **Observações:** 448
- **Cobertura geográfica:** BA, CE, GO, MA, MG, PE, PR, RJ, RS, SC, SP
- **Nº máx. de produtos distintos por estado:** 1
- **Nota:** Cluster homogêneo — produto único, sem necessidade de divisão em tiers

---

### BOPP/RAFIA

#### BOPP/RAFIA
- **Produtos:** PP RAFIA, SUCATA DE RAFIA
- **Observações:** 417
- **Cobertura geográfica:** MG, PR, RS, SC, SP
- **Nº máx. de produtos distintos por estado:** 2
- **Nota:** Cluster homogêneo — sem necessidade de divisão em tiers

---

### OUTROS (Materiais Diversos)

Grupo originalmente genérico que foi refinado em subgrupos especializados.

#### METAIS_DIVERSOS
- **Produtos:** SUCATA DE AEROSOL, SUCATA DE LATINHAS, SUCATA DE PLÁSTICO
- **Observações:** 1.628
- **Cobertura geográfica:** DF, ES, GO, MG, MS, PR, RJ, RN, SP
- **Nº máx. de produtos distintos por estado:** 3
- **Nota:** Separado dos plásticos por faixa de preço significativamente mais alta (8–12 R$/kg). Inclui alumínio, latinhas e outros metais.

#### OUTROS_PLASTICOS_MISTOS
- **Produtos:** PLÁSTICOS DIVERSOS, SUCATA DE PLÁSTICO
- **Observações:** 3.121
- **Cobertura geográfica:** AL, AM, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN, RS, SC, SE, SP
- **Nº máx. de produtos distintos por estado:** 2
- **Nota:** Maior cobertura geográfica (22 estados). Inclui plásticos que não se enquadram em nenhum tipo específico.

#### OUTROS_RESIDUAL
- **Produtos:** SUCATA DE AEROSOL, SUCATA DE BALDE BACIA PRETO
- **Observações:** 102
- **Cobertura geográfica:** BA, CE, GO, MG, RS, SP
- **Nº máx. de produtos distintos por estado:** 2
- **Nota:** Materiais residuais que não se encaixam nas demais classificações.

---

## Regras de Classificação

### Grupo Base (`material_group`)

| Grupo       | Regra de Detecção (na descrição do produto)            |
|:------------|:-------------------------------------------------------|
| PEAD        | Contém "PEAD"                                          |
| PET         | Contém "PET"                                           |
| BOPP/RAFIA  | Contém "BOPP" ou "RAFIA"                               |
| PP          | Contém "PP"                                            |
| PS          | Contém "PS"                                            |
| PVC         | Contém "PVC"                                           |
| PE/FILME    | Contém "PE " ou "FILME" ou começa com "PE"             |
| OUTROS      | Nenhuma das regras acima                                |

### Refinamento do OUTROS (`material_group_refined`)

| Subgrupo                 | Regra                                                               |
|:-------------------------|:--------------------------------------------------------------------|
| METAIS_DIVERSOS          | Preço > 4 R$/kg ou descrição contém LATIN/ALUMIN/LATA/COBRE        |
| OUTROS_PET               | Material = PET ou descrição contém "PET"                            |
| OUTROS_PEAD              | Descrição contém PEAD, FILME ou PEBD                                |
| OUTROS_PP                | Descrição contém PP ou POLIPROPILENO                                |
| OUTROS_PS                | Descrição contém PS                                                 |
| OUTROS_PVC               | Descrição contém PVC                                                |
| OUTROS_PLASTICOS_MISTOS  | Descrição contém PLAST ou SUCATA PLAST                              |
| OUTROS_PAPEIS            | Descrição contém PAPEL, CARTON ou PAPELAO                           |
| OUTROS_MADEIRA           | Descrição contém MADEIR, PALLET ou MACICA                           |
| OUTROS_RESIDUAL          | Nenhuma das regras acima                                            |

### Price Tiers

Dentro de cada grupo refinado, os produtos são segmentados em 3 faixas usando quantis da mediana de preço (calculada sobre dados de treino 2023–2024):

| Tier  | Faixa de Preço         |
|:------|:-----------------------|
| TIER1 | Quantil inferior (0–33%)  |
| TIER2 | Quantil médio (33–66%)    |
| TIER3 | Quantil superior (66–100%)|

Produtos com menos de 5 observações no treino não recebem tier.

---

## Resumo Quantitativo

| Cluster                  | Material Base  | Nº Observações | Nº Estados | Produtos Representativos                          |
|:-------------------------|:---------------|---------------:|-----------:|:--------------------------------------------------|
| PET_TIER3                | PET            |          3.810 |         14 | PET Cristal, PET Verde                            |
| OUTROS_PLASTICOS_MISTOS  | OUTROS         |          3.121 |         22 | Plásticos Diversos, Sucata de Plástico            |
| PP_TIER3                 | PP             |          1.870 |         12 | PP Branco, PP Margarina, PP Natural               |
| PEAD_TIER2               | PEAD           |          1.823 |         10 | Sucata de PEAD Colorido, PEAD Cristal             |
| METAIS_DIVERSOS          | OUTROS         |          1.628 |          9 | Sucata de Latinhas, Sucata de Aerosol             |
| PP_TIER1                 | PP             |          1.491 |         12 | PP Balde Bacia, PP Preto                          |
| PEAD_TIER3               | PEAD           |          1.368 |         10 | PEAD Bombona, Sucata de PEAD Branco               |
| PET_TIER2                | PET            |          1.365 |         14 | PET Colorido, Sucata de PET Leitoso               |
| PET_TIER1                | PET            |          1.309 |         11 | Fita PET Verde, PET Azeite, PET Óleo              |
| PVC                      | PVC            |            448 |         11 | Sucata de PVC                                     |
| PEAD_TIER1               | PEAD           |            448 |          5 | PEAD Misto, Sucata de PEAD Sacolinha              |
| BOPP/RAFIA               | BOPP/RAFIA     |            417 |          5 | PP Rafia, Sucata de Rafia                         |
| PE/FILME_TIER2           | PE/FILME       |            232 |          7 | Sucata de Filme Colorido                          |
| PS_TIER3                 | PS             |            138 |          4 | PS Copinho                                        |
| PP_TIER2                 | PP             |            137 |          3 | Sucata de PP Mineral, Sucata de PP Tampinha        |
| OUTROS_RESIDUAL          | OUTROS         |            102 |          6 | Sucata de Aerosol, Sucata de Balde Bacia Preto    |
| PE/FILME_TIER1           | PE/FILME       |             78 |          3 | PE Preto / PE Colorido                            |
| PS_TIER1                 | PS             |             53 |          1 | Sucata de PS Preto                                |
| PE/FILME_TIER3           | PE/FILME       |             41 |          3 | PE Canela                                         |
| PEAD                     | PEAD           |             30 |          1 | PEAD Cristal                                      |
| PP                       | PP             |             12 |          2 | Fita PP Branca, Fita PP Preta                     |
| PE/FILME                 | PE/FILME       |             10 |          1 | Sucata de Filme Canela, Sucata de Filme Preto      |
| PS_TIER2                 | PS             |             10 |          1 | Sucata de PS Copinho                              |
| PET                      | PET            |              6 |          1 | Sucata de PET Âmbar, Sucata PET Cristal e Verde   |
