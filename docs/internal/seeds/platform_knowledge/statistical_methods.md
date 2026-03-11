# Métodos Estatísticos para Análise de Dados de Negócios

## 1. Medidas de Tendência Central

### Média (Mean)
A média aritmética é a soma de todos os valores dividida pelo número de observações.
- **Fórmula**: $\bar{x} = \frac{\sum_{i=1}^{n} x_i}{n}$
- **Quando usar**: Dados simétricos sem outliers significativos.
- **Limitação**: Sensível a valores extremos (outliers). Um único valor muito alto pode distorcer a média.
- **Exemplo de negócio**: Ticket médio de vendas, salário médio dos funcionários.

### Mediana (Median)
O valor central quando os dados estão ordenados.
- **Quando usar**: Dados assimétricos ou com outliers. Mais robusta que a média.
- **Exemplo**: Mediana do tempo de resposta ao cliente (evita distorção por tickets complexos).

### Moda (Mode)
O valor mais frequente no conjunto de dados.
- **Quando usar**: Dados categóricos ou para identificar o valor mais comum.
- **Exemplo**: Produto mais vendido, forma de pagamento mais utilizada.

## 2. Medidas de Dispersão

### Desvio Padrão (Standard Deviation)
Mede o quão dispersos os dados estão em relação à média.
- **Desvio padrão baixo**: Dados concentrados próximos à média (consistência).
- **Desvio padrão alto**: Dados muito espalhados (variabilidade).
- **Exemplo**: Variabilidade no tempo de entrega — desvio padrão alto indica inconsistência logística.

### Variância (Variance)
O quadrado do desvio padrão. Menos intuitiva, mas essencial em modelos estatísticos.

### Coeficiente de Variação (CV)
Razão entre desvio padrão e média, expressa em porcentagem. Permite comparar variabilidade entre grupos com escalas diferentes.
- **CV < 15%**: Baixa dispersão.
- **CV entre 15-30%**: Dispersão moderada.
- **CV > 30%**: Alta dispersão.

### Amplitude (Range)
Diferença entre o maior e o menor valor. Simples mas sensível a outliers.

### Intervalo Interquartil (IQR)
Diferença entre o terceiro quartil (Q3) e o primeiro quartil (Q1). Robusto contra outliers.
- **Uso**: Identificação de outliers — valores abaixo de Q1 - 1.5×IQR ou acima de Q3 + 1.5×IQR.

## 3. Distribuições Estatísticas

### Distribuição Normal (Gaussiana)
- Curva em forma de sino, simétrica em torno da média.
- **Regra 68-95-99.7**: 68% dos dados dentro de 1σ, 95% dentro de 2σ, 99.7% dentro de 3σ.
- **Aplicação**: Controle de qualidade, análise de processo, precificação.

### Distribuição Log-Normal
- Comum em dados financeiros (preços de ações, receitas).
- Assimétrica à direita — muitos valores pequenos, poucos valores muito grandes.

### Distribuição de Poisson
- Modela contagem de eventos em um intervalo (tempo ou espaço).
- **Exemplos**: Número de chamadas por hora no call center, número de defeitos por lote.

### Distribuição Binomial
- Modela o número de sucessos em n tentativas independentes.
- **Exemplo**: Taxa de conversão — de 100 visitantes, quantos compram?

## 4. Teste de Hipóteses

### Conceitos Fundamentais
- **Hipótese nula (H₀)**: Não há efeito/diferença (status quo).
- **Hipótese alternativa (H₁)**: Existe efeito/diferença.
- **p-valor**: Probabilidade de observar os dados se H₀ fosse verdadeira.
  - p < 0.05 → Rejeitar H₀ (resultado estatisticamente significativo).
  - p ≥ 0.05 → Não rejeitar H₀ (insuficiente evidência).
- **Nível de significância (α)**: Tipicamente 0.05 (5%).
- **Erro Tipo I**: Rejeitar H₀ quando é verdadeira (falso positivo).
- **Erro Tipo II**: Não rejeitar H₀ quando é falsa (falso negativo).

### Teste t de Student
- Compara médias de dois grupos.
- **Independente**: Dois grupos diferentes (ex: vendas loja A vs loja B).
- **Pareado**: Mesmo grupo antes e depois (ex: vendas antes e depois de uma promoção).
- **Requisito**: Dados aproximadamente normais, amostras > 30 para relaxar.

### Teste Qui-Quadrado (Chi-Square)
- Testa associação entre variáveis categóricas.
- **Exemplo**: Existe relação entre região e preferência de produto?

### ANOVA (Análise de Variância)
- Compara médias de 3 ou mais grupos.
- **One-way**: Um fator (ex: vendas por região — Norte, Sul, Sudeste).
- **Two-way**: Dois fatores (ex: vendas por região × canal de vendas).
- **Post-hoc (Tukey)**: Identifica quais pares de grupos diferem.

### Teste de Mann-Whitney U
- Alternativa não paramétrica ao teste t (quando dados não são normais).
- Compara medianas em vez de médias.

## 5. Correlação e Regressão

### Correlação de Pearson
- Mede relação linear entre duas variáveis contínuas.
- **r = 1**: Correlação positiva perfeita.
- **r = 0**: Sem correlação linear.
- **r = -1**: Correlação negativa perfeita.
- **Cuidado**: Correlação ≠ causalidade!

### Correlação de Spearman
- Alternativa não paramétrica. Mede relação monotônica (não necessariamente linear).
- Ideal para dados ordinais ou com outliers.

### Regressão Linear Simples
- Modelo: y = β₀ + β₁x + ε
- **R²**: Proporção da variância explicada pelo modelo (0 a 1).
- **Exemplo**: Receita = f(investimento em marketing).

### Regressão Linear Múltipla
- Múltiplas variáveis independentes: y = β₀ + β₁x₁ + β₂x₂ + ... + ε
- **Cuidado com multicolinearidade**: Variáveis independentes não devem ser altamente correlacionadas entre si.

### Regressão Logística
- Variável dependente binária (sim/não, compra/não compra).
- Saída: Probabilidade entre 0 e 1.
- **Exemplo**: Probabilidade de churn dado perfil do cliente.

## 6. Análise de Séries Temporais

### Componentes
- **Tendência (Trend)**: Direção de longo prazo (crescente, decrescente, estável).
- **Sazonalidade (Seasonality)**: Padrões que se repetem em intervalos regulares.
- **Ciclicidade (Cyclicality)**: Flutuações de longo prazo sem período fixo.
- **Ruído (Noise)**: Variação aleatória.

### Médias Móveis
- **Simples (SMA)**: Média dos últimos n períodos. Suaviza ruído.
- **Exponencial (EMA)**: Peso maior para valores mais recentes.

### Decomposição
- Separar a série em tendência + sazonalidade + resíduo.
- **Aditiva**: Quando a amplitude sazonal é constante.
- **Multiplicativa**: Quando a amplitude sazonal cresce com o nível.

### Previsão (Forecasting)
- **ARIMA**: Auto-Regressive Integrated Moving Average. Padrão para séries estacionárias.
- **Prophet (Facebook)**: Bom para dados de negócio com sazonalidade múltipla + feriados.
- **Holt-Winters**: Suavização exponencial com tendência e sazonalidade.

## 7. Análise de Outliers

### Métodos de Detecção
- **Z-Score**: |z| > 3 é considerado outlier (assume distribuição normal).
- **IQR**: Valor < Q1 - 1.5×IQR ou > Q3 + 1.5×IQR.
- **Isolation Forest**: Algoritmo de machine learning para detecção de anomalias.

### Decisão sobre Outliers
1. **Verificar se é erro de dados** → Corrigir ou remover.
2. **Verificar se é evento real** → Documentar e decidir se mantém na análise.
3. **Usar métodos robustos** → Mediana, IQR, regressão robusta.

## 8. Amostragem

### Tipos
- **Aleatória simples**: Todo elemento tem igual probabilidade de ser selecionado.
- **Estratificada**: Divide população em estratos (ex: por região) e amostra de cada.
- **Sistemática**: Seleciona a cada k-ésimo elemento.
- **Por conglomerados (clusters)**: Seleciona grupos inteiros aleatoriamente.

### Tamanho da Amostra
- Para estimativa de proporção: $n = \frac{Z^2 \times p(1-p)}{e^2}$
  - Z = 1.96 para 95% de confiança
  - p = proporção esperada
  - e = margem de erro
- **Regra prática**: Mínimo de 30 observações por grupo para o Teorema Central do Limite.

## 9. Intervalos de Confiança

- **IC 95%**: Temos 95% de confiança que o verdadeiro parâmetro está neste intervalo.
- **Fórmula para média**: $\bar{x} \pm z_{\alpha/2} \times \frac{s}{\sqrt{n}}$
- **Interpretação para negócios**: "O ticket médio está entre R$ 45 e R$ 55 com 95% de confiança."

## 10. Métricas de Concordância e Qualidade de Modelo

### Para Classificação
- **Acurácia**: Proporção de predições corretas.
- **Precisão**: Dos que o modelo disse "sim", quantos realmente são "sim".
- **Recall (Sensibilidade)**: Dos que realmente são "sim", quantos o modelo acertou.
- **F1-Score**: Média harmônica de precisão e recall.
- **AUC-ROC**: Área sob a curva ROC. 0.5 = aleatório, 1.0 = perfeito.

### Para Regressão
- **MAE (Mean Absolute Error)**: Erro médio absoluto.
- **RMSE (Root Mean Square Error)**: Penaliza erros grandes mais fortemente.
- **MAPE (Mean Absolute Percentage Error)**: Erro percentual médio. Cuidado com valores próximos de zero.
- **R²**: Proporção da variância explicada (0 a 1).
