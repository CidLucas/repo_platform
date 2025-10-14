import asyncio
import os
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LXMLWebScrapingStrategy, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def main():
    """
    Função principal que orquestra o processo de scraping de múltiplos sites,
    filtra o conteúdo para manter apenas o relevante e salva o resultado
    consolidado em um único arquivo Markdown.
    """
    sites_to_crawl = [
        {"name": "pytest", "start_url": "https://docs.pytest.org/en/stable/how-to/index.html#how-to"}
    ]
    all_results_markdown = []

    # --- CAMADA 2: FILTRO DE CONTEÚDO INTELIGENTE ---
    # Este filtro remove blocos de texto com baixa densidade de conteúdo.
    # É excelente para limpar o "ruído" que a exclusão de tags não pega.
    prune_filter = PruningContentFilter(
        threshold=0.45,           # Limiar de pontuação para manter um bloco (ajuste conforme necessário)
        threshold_type="dynamic", # O filtro se adapta ao tipo de tag
        min_word_threshold=20     # Blocos com menos de 20 palavras são descartados
    )

    # --- CONFIGURAÇÃO DO GERADOR DE MARKDOWN COM O FILTRO ---
    md_generator = DefaultMarkdownGenerator(
        content_filter=prune_filter
    )

    # --- CONFIGURAÇÃO DO CRAWLER COM AS MELHORES PRÁTICAS ---
    config = CrawlerRunConfig(
        # Estratégia de crawling profundo (1 nível a partir da URL inicial)
        deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=1, include_external=False),

        # Estratégia de scraping performática
        scraping_strategy=LXMLWebScrapingStrategy(),

        # Gerador de markdown com nosso filtro de limpeza
        markdown_generator=md_generator,

        # --- CAMADA 1: EXCLUSÃO EXPLÍCITA DE TAGS DE NAVEGAÇÃO ---
        # A forma mais eficiente de remover menus, cabeçalhos e rodapés.
        excluded_tags=["header", "footer"],

        # Ignorar cache para garantir que sempre tenhamos a documentação mais recente
        cache_mode=CacheMode.BYPASS,

        verbose=True
    )

    print("Iniciando o processo de scraping...")
    async with AsyncWebCrawler() as crawler:
        for site in sites_to_crawl:
            site_name = site["name"]
            # Um nome de arquivo mais agnóstico
            output_filename = "f'{site_name}Docs.md"
            start_url = site["start_url"]
            print(f"\n--- Processando: {site_name} ---")

            try:
                # O deep_crawl retorna uma lista de resultados
                results = await crawler.arun(url=start_url, config=config)

                if not isinstance(results, list):
                    results = [results] # Garante que sempre seja uma lista para o loop

                all_results_markdown.append(f"# Documentação de {site_name}\n\n")

                for result_doc in results:
                    if result_doc and result_doc.success and result_doc.markdown:
                        # Usamos o 'fit_markdown', que é o resultado após a aplicação do PruningContentFilter
                        # Se não houver filtro, pode-se usar o 'raw_markdown'
                        markdown_content = result_doc.markdown.fit_markdown or result_doc.markdown.raw_markdown

                        # Uma verificação extra para não adicionar páginas vazias
                        if len(markdown_content.strip()) > 100:
                             all_results_markdown.append(f"## Fonte: {result_doc.url}\n\n{markdown_content}\n\n---\n\n")

                print(f"Finalizado: {site_name}. {len(results)} páginas processadas.")

            except Exception as e:
                print(f"Erro ao processar {site_name}: {e}")
                all_results_markdown.append(f"# ERRO ao processar {site_name}\n\nURL: {start_url}\nErro: {e}\n\n---\n\n")

    print(f"\nSalvando todo o conteúdo no arquivo: {output_filename}")
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("".join(all_results_markdown))
        print(f"Arquivo '{output_filename}' salvo com sucesso!")
        print(f"Caminho completo: {os.path.abspath(output_filename)}")
    except IOError as e:
        print(f"Erro ao salvar o arquivo: {e}")

if __name__ == "__main__":
    asyncio.run(main())