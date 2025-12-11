#!/usr/bin/env python3
"""
Script para extrair conteúdo completo do site annamariamaiolino.com
Salva estrutura, textos, imagens e URLs para uso no Figma/redesign
"""

import json
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# URLs das páginas
PAGES = {
    "home": "https://annamariamaiolino.com/",
    "menu": "https://annamariamaiolino.com/menu-amm.html",
    "linha_do_tempo": "https://annamariamaiolino.com/linha-do-tempo-amm.html",
    "obras": "https://annamariamaiolino.com/obras-amm.html",
    "textos_criticos": "https://annamariamaiolino.com/textos-amm.html",
    "sine_die": "https://annamariamaiolino.com/sinedie-amm.html",
    "textos_arte_anna": "https://annamariamaiolino.com/textos-arte-anna-amm.html",
    "contato": "https://annamariamaiolino.com/contato-amm.html",
}

def extract_page_content(url: str, page_name: str) -> dict:
    """Extrai conteúdo de uma página"""
    print(f"📄 Extraindo: {page_name} ({url})")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extrai meta informações
        title = soup.find('title').text if soup.find('title') else page_name
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '') if meta_desc else ''

        # Extrai todos os textos (parágrafos, headings)
        texts = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div']):
            text = tag.get_text(strip=True)
            if text and len(text) > 5:  # Apenas textos significativos
                texts.append({
                    'tag': tag.name,
                    'text': text
                })

        # Extrai imagens
        images = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            if src:
                full_url = urljoin(url, src)
                images.append({
                    'src': full_url,
                    'alt': alt,
                    'original_src': src
                })

        # Extrai links
        links = []
        for link in soup.find_all('a'):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if href and text:
                links.append({
                    'href': href,
                    'text': text
                })

        # Extrai estrutura (divs com classes/ids importantes)
        sections = []
        for div in soup.find_all(['section', 'article', 'div'], class_=True):
            class_name = ' '.join(div.get('class', []))
            section_text = div.get_text(strip=True)[:200]  # Primeiros 200 caracteres
            if section_text:
                sections.append({
                    'class': class_name,
                    'content_preview': section_text
                })

        return {
            'page': page_name,
            'url': url,
            'title': title,
            'description': description,
            'total_texts': len(texts),
            'total_images': len(images),
            'total_links': len(links),
            'total_sections': len(sections),
            'texts': texts[:50],  # Top 50 textos
            'images': images,
            'links': links,
            'sections': sections[:20]  # Top 20 seções
        }

    except Exception as e:
        print(f"❌ Erro ao extrair {page_name}: {e}")
        return {
            'page': page_name,
            'url': url,
            'error': str(e)
        }

def main():
    """Extrai todas as páginas"""
    print("🚀 Iniciando extração do site anna maria maiolino...\n")

    all_content = {}

    for page_name, url in PAGES.items():
        content = extract_page_content(url, page_name)
        all_content[page_name] = content
        time.sleep(1)  # Respeita o servidor

    # Salva em JSON
    output_file = '/Users/tarsobarreto/Documents/vizu-mono/ferramentas/anna_site_content.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_content, f, ensure_ascii=False, indent=2)

    print("\n✅ Extração concluída!")
    print(f"📁 Conteúdo salvo em: {output_file}")

    # Mostra resumo
    print("\n📊 RESUMO:")
    for page_name, content in all_content.items():
        if 'error' not in content:
            print(f"  {page_name}: {content['total_texts']} textos, {content['total_images']} imagens")
        else:
            print(f"  {page_name}: ❌ {content['error']}")

if __name__ == '__main__':
    main()
