import asyncio
import os
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def main():
    """
    Função principal que orquestra o processo de scraping de múltiplos sites
    e salva o conteúdo consolidado em um único arquivo Markdown.
    """
    # Lista de sites a serem processados.
    # Esta estrutura permite adicionar ou remover fontes facilmente.
    sites_to_crawl = [
        {
            "name": "SQL Alchemy Documentation",
            "start_url": "https://docs.sqlalchemy.org/en/20/core"
        }
    ]

    # Nome do arquivo de saída
    output_filename = "scraped_documentation.md"
    all_results_markdown = []

    # --- Configuração do Crawler (reutilizável para todos os sites) ---
    prune_filter = PruningContentFilter(
        threshold=0.45,
        threshold_type="dynamic",
        min_word_threshold=30
    )
    md_generator = DefaultMarkdownGenerator(content_filter=prune_filter)
    config = CrawlerRunConfig(
        markdown_generator=md_generator,
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=1,
            include_external=False
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True # Mantenha True para depuração, considere False em produção
    )
    # --- Fim da Configuração ---

    print("Iniciando o processo de scraping...")

    async with AsyncWebCrawler() as crawler:
        for site in sites_to_crawl:
            site_name = site["name"]
            start_url = site["start_url"]
            print(f"\n--- Processando: {site_name} ---")

            try:
                # Executa o scraping para o site atual
                results = await crawler.arun(start_url, config=config)

                # Adiciona um cabeçalho para separar o conteúdo de cada site
                all_results_markdown.append(f"# Documentação de {site_name}\n\n")

                # Itera sobre os resultados e extrai o conteúdo Markdown
                for result in results:
                    if result.markdown:
                        all_results_markdown.append(f"## Fonte: {result.url}\n\n{result.markdown.fit_markdown}\n\n---\n\n")

                print(f"Finalizado: {site_name}. {len(results)} páginas processadas.")

            except Exception as e:
                print(f"Erro ao processar {site_name}: {e}")
                # Opcional: Adicionar um log do erro no arquivo final
                all_results_markdown.append(f"# ERRO ao processar {site_name}\n\nURL: {start_url}\nErro: {e}\n\n---\n\n")


    # --- Salvando o conteúdo consolidado em um arquivo ---
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