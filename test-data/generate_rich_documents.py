#!/usr/bin/env python3
"""Gerador de documentos ricos para as 3 personas do Blu.

Gera PDFs escaneados (DANFE, NFSe), extratos bancários, cardápios,
materiais de divulgação, contratos assinados e propostas detalhadas.

Requisitos: pip install fpdf2 Pillow
"""

import csv
import os
import random
import io
from datetime import date, timedelta, datetime
from pathlib import Path

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False
    print("[ERRO] fpdf2 não instalado. pip install fpdf2")
    raise

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[aviso] Pillow não instalado — pulando imagens.")

random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSONAS_DIR = os.path.join(BASE_DIR, "personas")
TODAY = date(2026, 6, 24)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
# CLASSE BASE DE PDF COM ESTILO "DOCUMENTO REAL"
# ═══════════════════════════════════════════════════════════════════════════

class DocPDF(FPDF):
    """PDF base com fonte, cores e layout de documento empresarial."""

    def __init__(self, title="Documento"):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(auto=True, margin=20)
        # Adicionar fonte Unicode
        self.add_font("DejaVu", "", "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf")
        self.add_font("DejaVu", "B", "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf")
        self.title_doc = title

    def header_custom(self, title, subtitle=""):
        """Cabeçalho padronizado."""
        self.set_font("DejaVu", "B", 16)
        self.set_text_color(30, 60, 120)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        if subtitle:
            self.set_font("DejaVu", "", 9)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, subtitle, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(30, 60, 120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def section_title(self, title):
        self.set_font("DejaVu", "B", 11)
        self.set_text_color(60, 60, 60)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def section_body(self, text):
        self.set_font("DejaVu", "", 9)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 4.5, text)
        self.ln(2)

    def table_row(self, cells, widths=None, bold=False, fill=False):
        """Desenha uma linha de tabela."""
        if widths is None:
            w = 190 / max(len(cells), 1)
            widths = [w] * len(cells)
        self.set_font("DejaVu", "B" if bold else "", 8)
        if fill:
            self.set_fill_color(230, 235, 245)
        else:
            self.set_fill_color(255, 255, 255)
        self.set_text_color(40, 40, 40)
        x_start = self.get_x()
        y = self.get_y()
        max_h = 5
        for i, cell_text in enumerate(cells):
            self.set_xy(x_start + sum(widths[:i]), y)
            self.cell(widths[i], 5, str(cell_text), border=1, fill=fill, align="C" if i > 0 else "L")
        self.set_y(y + 5)

    def watermark(self, text="DOCUMENTO DE TESTE"):
        """Marca d'água de teste."""
        self.set_font("DejaVu", "B", 60)
        self.set_text_color(220, 220, 220)
        self.set_xy(20, 100)
        self.cell(0, 40, text, align="C")


# ═══════════════════════════════════════════════════════════════════════════
# 1. NFSe ESCANEADA — CAROLINA (Designer)
# ═══════════════════════════════════════════════════════════════════════════

def gerar_nfse_carolina():
    """Gera PDFs de NFSe (Nota Fiscal de Serviços) para Carolina."""
    base = os.path.join(PERSONAS_DIR, "carolina-design", "documentos-ruido", "nfs_escaneadas")
    ensure_dir(base)

    # Dados de NFs específicas (baseado no descritivo)
    notas = [
        {
            "numero": "NFSE-2025-0001",
            "data": "10/06/2025",
            "tomador": "Buffet Lúcia's Food",
            "cnpj_tomador": "48.792.305/0001-81",
            "servico": "Criação de logotipo e cardápio digital",
            "valor": "R$ 2.500,00",
            "iss": "R$ 125,00",
            "liquido": "R$ 2.375,00",
            "codigo_verificacao": "ABCD-1234-EFGH-5678",
        },
        {
            "numero": "NFSE-2025-0012",
            "data": "20/02/2025",
            "tomador": "NovaTech Soluções em TI",
            "cnpj_tomador": "32.718.694/0001-07",
            "servico": "Criação de logotipo e identidade visual",
            "valor": "R$ 3.500,00",
            "iss": "R$ 175,00",
            "liquido": "R$ 3.325,00",
            "codigo_verificacao": "WXYZ-9876-LMNO-5432",
        },
        {
            "numero": "NFSE-2025-0033",
            "data": "05/04/2025",
            "tomador": "Padaria Vitória",
            "cnpj_tomador": "12.345.678/0001-00",
            "servico": "Design de folder promocional + banner",
            "valor": "R$ 1.800,00",
            "iss": "R$ 90,00",
            "liquido": "R$ 1.710,00",
            "codigo_verificacao": "PLOK-0987-MJNH-6543",
        },
    ]

    for nf in notas:
        pdf = DocPDF(f"NFSe_{nf['numero']}")
        pdf.add_page()

        # Moldura de documento oficial
        pdf.set_draw_color(0, 0, 0)
        pdf.rect(8, 8, 194, 280)

        # Selo "TESTE" decorativo
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(180, 180, 180)
        pdf.set_xy(150, 10)
        pdf.cell(45, 5, "DOCUMENTO DE TESTE - SEM VALOR FISCAL", align="R")

        # Cabeçalho
        pdf.set_font("DejaVu", "B", 14)
        pdf.set_text_color(30, 60, 120)
        pdf.set_xy(15, 20)
        pdf.cell(0, 8, "NOTA FISCAL DE SERVIÇOS ELETRÔNICA - NFSe", align="C")
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(80, 80, 80)
        pdf.set_xy(15, 28)
        pdf.cell(0, 4, "Prefeitura do Município de São Paulo - Sistema Paulistano", align="C")

        # QR Code placeholder
        pdf.set_draw_color(0, 0, 0)
        pdf.rect(160, 35, 30, 30)
        pdf.set_font("DejaVu", "", 5)
        pdf.set_xy(160, 48)
        pdf.cell(30, 4, "(QR Code de consulta)", align="C")

        # Dados da nota
        pdf.set_xy(15, 38)
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(40, 40, 40)

        # Número em destaque
        pdf.set_font("DejaVu", "B", 22)
        pdf.set_text_color(200, 50, 50)
        pdf.set_xy(15, 42)
        pdf.cell(0, 10, f"Nº {nf['numero']}", align="L")

        # Dados do prestador
        y = 56
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.set_xy(15, y)
        pdf.cell(0, 6, "PRESTADOR DE SERVIÇOS")
        pdf.set_font("DejaVu", "", 9)
        pdf.set_xy(20, y + 7)
        pdf.cell(0, 5, "Carolina Mendes de Oliveira")
        pdf.set_xy(20, y + 12)
        pdf.cell(0, 5, "CPF: 384.029.170-50 | Insc. Municipal: 8.765.432-1")
        pdf.set_xy(20, y + 17)
        pdf.cell(0, 5, "Rua Artur de Azevedo, 1040, apto 72 - Pinheiros, SP - CEP 05404-003")

        # Dados do tomador
        y += 28
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_xy(15, y)
        pdf.cell(0, 6, "TOMADOR DE SERVIÇOS")
        pdf.set_font("DejaVu", "", 9)
        pdf.set_xy(20, y + 7)
        pdf.cell(0, 5, nf["tomador"])
        pdf.set_xy(20, y + 12)
        pdf.cell(0, 5, f"CNPJ/CPF: {nf['cnpj_tomador']}")

        # Dados do serviço
        y += 24
        pdf.set_draw_color(200, 200, 200)
        pdf.line(15, y, 195, y)
        y += 5
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_xy(15, y)
        pdf.cell(0, 6, "DISCRIMINAÇÃO DO SERVIÇO")
        pdf.set_font("DejaVu", "", 9)
        pdf.set_xy(20, y + 8)
        pdf.cell(0, 5, nf["servico"])
        pdf.set_xy(20, y + 14)
        pdf.cell(0, 5, f"Data de emissão: {nf['data']}")
        pdf.set_xy(20, y + 19)
        pdf.cell(0, 5, "Item LC 116: 08.02 - Serviços de design gráfico")

        # Valores
        y += 30
        pdf.set_draw_color(200, 200, 200)
        pdf.line(15, y, 195, y)
        y += 5
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_xy(15, y)
        pdf.cell(0, 6, "VALORES")

        fields = [
            ("Valor do Serviço:", nf["valor"]),
            ("Deduções:", "R$ 0,00"),
            ("Base de Cálculo do ISS:", nf["valor"]),
            ("Alíquota ISS:", "5,00%"),
            ("Valor do ISS:", nf["iss"]),
            ("ISS Retido na Fonte:", "Não"),
            ("Valor Líquido:", nf["liquido"]),
        ]
        for i, (label, value) in enumerate(fields):
            row_y = y + 7 + i * 6
            bold = "B" if label in ("Valor Líquido:", "Valor do Serviço:") else ""
            pdf.set_font("DejaVu", bold, 9)
            pdf.set_xy(20, row_y)
            pdf.cell(70, 5, label)
            pdf.set_x(120)
            pdf.cell(60, 5, value, align="R")

        # Código de verificação
        y += 7 + len(fields) * 6 + 10
        pdf.set_draw_color(200, 200, 200)
        pdf.line(15, y, 195, y)
        y += 5
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_xy(15, y)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, f"Código de Verificação: {nf['codigo_verificacao']}")
        pdf.set_xy(15, y + 5)
        pdf.cell(0, 5, f"Consulte em: https://nfse.prefeitura.sp.gov.br/consulta")

        path = os.path.join(base, f"nfse_{nf['numero']}.pdf")
        pdf.output(path)
        print(f"  ✓ NFSe PDF: {path}")


# ═══════════════════════════════════════════════════════════════════════════
# 2. DANFE (NF-e) ESCANEADO — LÚCIA (Buffet) e NOVATECH
# ═══════════════════════════════════════════════════════════════════════════

def gerar_danfe_lucia():
    """Gera DANFE (Documento Auxiliar NF-e) para Lúcia."""
    base = os.path.join(PERSONAS_DIR, "lucia-buffet", "documentos-ruido", "nfs_escaneadas")
    ensure_dir(base)

    notas = [
        {
            "chave": "3520 0648 7923 0500 0181 5500 1000 0000 0110 0000 0011",
            "numero": "000.000.011",
            "serie": "1",
            "data": "07/12/2025",
            "hora": "10:00:00",
            "destinatario": "Roberto Silva e Camila Costa",
            "cpf_dest": "401.273.658-90",
            "produto": "Buffet Completo Casamento - 200 convidados",
            "valor": "R$ 18.500,00",
            "tributos": "R$ 4.320,00",
            "natureza": "VENDA",
            "obs": "PREJUÍZO - Compareceram apenas 130 convidados",
        },
        {
            "chave": "3520 0648 7923 0500 0181 5500 1000 0000 0210 0000 0022",
            "numero": "000.000.022",
            "serie": "1",
            "data": "22/11/2025",
            "hora": "14:30:00",
            "destinatario": "Salão Villa Flora Eventos",
            "cpf_dest": "44.555.666/0001-77",
            "produto": "Coquetel inauguração nova ala",
            "valor": "R$ 3.200,00",
            "tributos": "R$ 640,00",
            "natureza": "VENDA",
            "obs": "Comissão informal Eliane 10%",
        },
        {
            "chave": "3520 0648 7923 0500 0181 5500 1000 0000 0310 0000 0033",
            "numero": "000.000.033",
            "serie": "1",
            "data": "20/06/2025",
            "hora": "09:15:00",
            "destinatario": "Colégio São Miguel",
            "cpf_dest": "11.234.567/0001-90",
            "produto": "Buffet Festa Junina - 300 pessoas",
            "valor": "R$ 4.500,00",
            "tributos": "R$ 810,00",
            "natureza": "VENDA",
            "obs": "Tradicional - todo ano",
        },
    ]

    for nf in notas:
        pdf = DocPDF(f"DANFE_{nf['numero']}")
        pdf.add_page()

        # Layout DANFE
        # Topo — chave de acesso
        pdf.set_fill_color(30, 60, 120)
        pdf.rect(8, 8, 194, 15, 'F')
        pdf.set_font("DejaVu", "B", 7)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(12, 10)
        pdf.cell(0, 4, "DANFE - Documento Auxiliar da Nota Fiscal Eletrônica")
        pdf.set_xy(12, 15)
        pdf.cell(0, 4, f"Chave de Acesso: {nf['chave']}")

        # Código de barras simulado
        pdf.set_fill_color(255, 255, 255)
        barcode_y = 25
        pdf.rect(15, barcode_y, 170, 20, 'F')
        pdf.set_draw_color(0, 0, 0)
        for i in range(0, 170, 3):
            h = random.randint(8, 18)
            pdf.line(15+i, barcode_y + 20 - h, 15+i, barcode_y + 20)
        # Número abaixo do código
        pdf.set_font("DejaVu", "", 6)
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(15, barcode_y + 21)
        chave_curta = nf['chave'].replace(" ", "")
        pdf.cell(170, 4, f"Consulte pela chave de acesso em http://www.sefaz.sp.gov.br/nfe", align="C")

        # Protocolo
        y = 50
        pdf.set_fill_color(240, 240, 245)
        pdf.rect(8, y, 194, 10, 'F')
        pdf.set_font("DejaVu", "", 7)
        pdf.set_text_color(80, 80, 80)
        pdf.set_xy(12, y+1)
        np = f"{''.join([str(random.randint(0,9)) for _ in range(15)])}"
        pdf.cell(0, 4, f"Protocolo de Autorização: {np} - {nf['data']} {nf['hora']}")

        # Dados emitente
        y = 62
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(30, 60, 120)
        pdf.set_xy(12, y)
        pdf.cell(0, 6, "LÚCIA'S FOOD BUFFET & CATERING")
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(40, 40, 40)
        pdf.set_xy(12, y + 7)
        pdf.cell(0, 4, "CNPJ: 48.792.305/0001-81 | IE: 789.456.123.789 | IM: 8.765.432-1")
        pdf.set_xy(12, y + 12)
        pdf.cell(0, 4, "Rua Silva Teles, 332 - Barra Funda - São Paulo/SP - CEP 01140-020")

        # Dados destinatário
        y += 22
        pdf.set_fill_color(240, 240, 245)
        pdf.rect(8, y, 194, 15, 'F')
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(40, 40, 40)
        pdf.set_xy(12, y + 1)
        pdf.cell(0, 5, f"DESTINATÁRIO: {nf['destinatario']}")
        pdf.set_font("DejaVu", "", 8)
        pdf.set_xy(12, y + 7)
        pdf.cell(0, 4, f"CPF/CNPJ: {nf['cpf_dest']}")

        # Quadro de tributos
        y += 20
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(40, 40, 40)
        pdf.set_fill_color(230, 235, 245)
        headers = ["Descrição", "Valor"]
        col_widths = [150, 40]
        pdf.set_xy(12, y)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 6, h, border=1, fill=True, align="C" if i > 0 else "L")
        y += 6

        items = [
            ("Valor Total dos Produtos", f"{nf['valor']}"),
            ("Desconto", "R$ 0,00"),
            ("Base de Cálculo ICMS", f"R$ {float(nf['valor'].replace('R$ ','').replace('.','').replace(',','.'))*0.7:.2f}".replace('.',',')),
            ("Valor ICMS", f"R$ {float(nf['valor'].replace('R$ ','').replace('.','').replace(',','.'))*0.7*0.12:.2f}".replace('.',',')),
            ("Valor do PIS", f"R$ {float(nf['valor'].replace('R$ ','').replace('.','').replace(',','.'))*0.0165:.2f}".replace('.',',')),
            ("Valor da COFINS", f"R$ {float(nf['valor'].replace('R$ ','').replace('.','').replace(',','.'))*0.076:.2f}".replace('.',',')),
            ("Total Tributos", f"{nf['tributos']}"),
        ]
        pdf.set_font("DejaVu", "", 8)
        for label, val in items:
            pdf.set_xy(12, y)
            pdf.cell(150, 5, label, border=1)
            pdf.cell(40, 5, val, border=1, align="R")
            y += 5

        # Total em destaque
        pdf.set_fill_color(255, 240, 240)
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(180, 0, 0)
        pdf.set_xy(12, y)
        pdf.cell(150, 7, "VALOR TOTAL DA NOTA:", border=1, fill=True)
        pdf.cell(40, 7, nf["valor"], border=1, fill=True, align="R")
        y += 9

        # Produto
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_fill_color(230, 235, 245)
        pdf.set_xy(12, y)
        pdf.cell(190, 6, "PRODUTO/SERVIÇO", border=1, fill=True)
        y += 6
        pdf.set_font("DejaVu", "", 8)
        pdf.set_xy(12, y)
        pdf.cell(190, 8, nf["produto"], border=1)
        y += 10

        # Observação
        if nf.get("obs"):
            pdf.set_font("DejaVu", "B", 8)
            pdf.set_text_color(180, 80, 0)
            pdf.set_xy(12, y)
            pdf.cell(190, 5, f"OBSERVAÇÃO: {nf['obs']}")

        # Rodapé
        y = 265
        pdf.set_font("DejaVu", "", 6)
        pdf.set_text_color(120, 120, 120)
        pdf.set_xy(12, y)
        pdf.cell(0, 3, f"DOCUMENTO DE TESTE - SEM VALOR FISCAL | DANFE gerado em {TODAY.isoformat()}")

        path = os.path.join(base, f"danfe_{nf['numero']}.pdf")
        pdf.output(path)
        print(f"  ✓ DANFE PDF (Lúcia): {path}")


def gerar_danfe_novatech():
    """Gera DANFE para vendas de hardware da NovaTech."""
    base = os.path.join(PERSONAS_DIR, "novatech-ti", "documentos-ruido", "nfs_escaneadas")
    ensure_dir(base)

    notas = [
        {
            "chave": "3520 0632 7186 9400 0107 5500 1000 0000 0110 0000 0011",
            "numero": "000.000.015",
            "serie": "1",
            "data": "15/03/2026",
            "hora": "11:22:00",
            "destinatario": "AutoPeças Lima Ltda.",
            "cnpj_dest": "11.222.333/0001-44",
            "produto": "10 Monitores Dell 24\" + 5 SSDs Kingston 480GB",
            "valor": "R$ 9.800,00",
            "tributos": "R$ 2.580,00",
            "natureza": "VENDA DE MERCADORIA ADQUIRIDA",
        },
        {
            "chave": "3520 0632 7186 9400 0107 5500 1000 0000 0210 0000 0022",
            "numero": "000.000.016",
            "serie": "1",
            "data": "01/03/2026",
            "hora": "09:45:00",
            "destinatario": "Construtora Novo Norte Ltda.",
            "cnpj_dest": "22.456.789/0001-10",
            "produto": "Projeto migração nuvem - 30 estações (serviço)",
            "valor": "R$ 45.000,00",
            "tributos": "R$ 8.100,00",
            "natureza": "PRESTAÇÃO DE SERVIÇO",
        },
        {
            "chave": "3520 0632 7186 9400 0107 5500 1000 0000 0310 0000 0033",
            "numero": "000.000.017",
            "serie": "1",
            "data": "20/01/2026",
            "hora": "14:00:00",
            "destinatario": "Colégio São Miguel",
            "cnpj_dest": "11.234.567/0001-90",
            "produto": "20 Chromebooks Samsung Educacional",
            "valor": "R$ 24.000,00",
            "tributos": "R$ 5.800,00",
            "natureza": "VENDA DE MERCADORIA ADQUIRIDA",
        },
    ]

    for nf in notas:
        pdf = DocPDF(f"DANFE_NT_{nf['numero']}")
        pdf.add_page()

        # Topo
        pdf.set_fill_color(30, 60, 120)
        pdf.rect(8, 8, 194, 15, 'F')
        pdf.set_font("DejaVu", "B", 7)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(12, 10)
        pdf.cell(0, 4, "DANFE - Documento Auxiliar da Nota Fiscal Eletrônica")
        pdf.set_xy(12, 15)
        pdf.cell(0, 4, f"Chave de Acesso: {nf['chave']}")

        # Código barras
        barcode_y = 25
        pdf.set_draw_color(0, 0, 0)
        for i in range(0, 170, 3):
            h = random.randint(8, 18)
            pdf.line(15+i, barcode_y + 20 - h, 15+i, barcode_y + 20)
        pdf.set_font("DejaVu", "", 6)
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(15, barcode_y + 21)
        pdf.cell(170, 4, "Consulte pela chave em http://www.sefaz.sp.gov.br/nfe", align="C")

        # Emitente
        y = 50
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(30, 60, 120)
        pdf.set_xy(12, y)
        pdf.cell(0, 6, "NOVATECH SOLUÇÕES EM INFORMÁTICA LTDA.")
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(40, 40, 40)
        pdf.set_xy(12, y + 7)
        pdf.cell(0, 4, "CNPJ: 32.718.694/0001-07 | IE: 456.789.012.345 | IM: 5.432.100-1 | CRT: 3")
        pdf.set_xy(12, y + 12)
        pdf.cell(0, 4, "Rua Itapura, 1850, sala 307 - Tatuapé - São Paulo/SP - CEP 03309-000")

        # Destinatário
        y += 22
        pdf.set_fill_color(240, 240, 245)
        pdf.rect(8, y, 194, 15, 'F')
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(40, 40, 40)
        pdf.set_xy(12, y + 1)
        pdf.cell(0, 5, f"DESTINATÁRIO: {nf['destinatario']}")
        pdf.set_font("DejaVu", "", 8)
        pdf.set_xy(12, y + 7)
        pdf.cell(0, 4, f"CNPJ: {nf['cnpj_dest']}")

        # Tributos
        y += 20
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_fill_color(230, 235, 245)
        pdf.set_xy(12, y)
        pdf.cell(150, 6, "Descrição", border=1, fill=True)
        pdf.cell(40, 6, "Valor", border=1, fill=True, align="C")
        y += 6

        itens = [
            ("Natureza da Operação", nf["natureza"]),
            ("Valor Total dos Produtos", nf["valor"]),
            ("Base de Cálculo ICMS", f"R$ {float(nf['valor'].replace('R$ ','').replace('.','').replace(',','.'))*0.8:.2f}".replace('.',',')),
            ("Valor ICMS (18%)", f"R$ {float(nf['valor'].replace('R$ ','').replace('.','').replace(',','.'))*0.8*0.18:.2f}".replace('.',',')),
            ("Valor do PIS", f"R$ {float(nf['valor'].replace('R$ ','').replace('.','').replace(',','.'))*0.0065:.2f}".replace('.',',')),
            ("Valor da COFINS", f"R$ {float(nf['valor'].replace('R$ ','').replace('.','').replace(',','.'))*0.03:.2f}".replace('.',',')),
            ("Total Tributos", nf["tributos"]),
        ]
        pdf.set_font("DejaVu", "", 8)
        for label, val in itens:
            pdf.set_xy(12, y)
            pdf.cell(150, 5, label, border=1)
            pdf.cell(40, 5, val, border=1, align="R")
            y += 5

        # Total
        pdf.set_fill_color(255, 240, 240)
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(180, 0, 0)
        pdf.set_xy(12, y)
        pdf.cell(150, 7, "VALOR TOTAL DA NOTA:", border=1, fill=True)
        pdf.cell(40, 7, nf["valor"], border=1, fill=True, align="R")
        y += 9

        # Produto
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_fill_color(230, 235, 245)
        pdf.set_xy(12, y)
        pdf.cell(190, 6, "PRODUTO/SERVIÇO", border=1, fill=True)
        y += 6
        pdf.set_font("DejaVu", "", 10)
        pdf.set_xy(12, y)
        pdf.cell(190, 20, f"    {nf['produto']}", border=1)

        path = os.path.join(base, f"danfe_novatech_{nf['numero']}.pdf")
        pdf.output(path)
        print(f"  ✓ DANFE PDF (NovaTech): {path}")


# ═══════════════════════════════════════════════════════════════════════════
# 3. EXTRATOS BANCÁRIOS — TODAS AS PERSONAS
# ═══════════════════════════════════════════════════════════════════════════

def gerar_extrato_nubank(nome_pessoa, slug, ident="", mes=6, ano=2026):
    """Gera extrato bancário no formato Nubank (CSV)."""
    base = os.path.join(PERSONAS_DIR, slug, "documentos-ruido", "extratos")
    ensure_dir(base)

    # Movimentação típica do mês
    movs = []
    if slug == "carolina-design":
        movs = [
            ("01/06/2026", 28.00, "GOOGLE WORKSPACE INDIVIDUAL"),
            ("03/06/2026", 401.00, "ADOBE CREATIVE CLOUD"),
            ("05/06/2026", 600.00, "PIX RECEBIDO - PILATES CORPO LIVRE"),
            ("08/06/2026", 150.00, "PIX ENVIADO - TRANSPORTADORA FLASH"),
            ("10/06/2026", 350.00, "PIX RECEBIDO - EMPORIO DA VILA"),
            ("12/06/2026", 89.90, "MERCADO LIVRE *SUPRIMENTOS"),
            ("15/06/2026", 1200.00, "PIX RECEBIDO - PADARIA VITORIA"),
            ("15/06/2026", 29.90, "SPOTIFY *PREMIUM"),
            ("18/06/2026", 85.00, "IFOOD *PEDIDO"),
            ("20/06/2026", 420.00, "PIX RECEBIDO - CLINICA VET SAUDE"),
            ("22/06/2026", 250.00, "PIX ENVIADO - GRAFICA NOVA ERA"),
            ("25/06/2026", 49.90, "NETFLIX"),
            ("28/06/2026", 200.00, "PIX RECEBIDO - ANA CLARA"),
        ]
    elif slug == "lucia-buffet":
        movs = [
            ("01/06/2026", 1500.00, "PIX RECEBIDO - DRA REGINA ADVOCACIA"),
            ("02/06/2026", 680.00, "PIX ENVIADO - ACUGUE DO ZE"),
            ("03/06/2026", 450.00, "PIX ENVIADO - CEAGESP"),
            ("05/06/2026", 4200.00, "PIX RECEBIDO - CONSTRUTORA NOVO NORTE"),
            ("05/06/2026", 3500.00, "TED - ALUGUEL COZINHA INDUSTRIAL"),
            ("07/06/2026", 380.00, "PIX ENVIADO - EMBALAGENS PREMIUM"),
            ("08/06/2026", 2800.00, "TED - SALARIO ROSA MARIA"),
            ("08/06/2026", 1600.00, "TED - SALARIO FRANCISCO"),
            ("10/06/2026", 220.00, "PIX ENVIADO - GAS E EQUIPAMENTOS"),
            ("12/06/2026", 1200.00, "PIX RECEBIDO - COLEGIO SAO MIGUEL"),
            ("15/06/2026", 950.00, "PIX RECEBIDO - COFFEE BREAK NOVO NORTE"),
            ("15/06/2026", 900.00, "PIX ENVIADO - MERCEARIA DO PORTO"),
            ("18/06/2026", 650.00, "PIX ENVIADO - CASA DOS FRIOS"),
            ("20/06/2026", 850.00, "PIX ENVIADO - DISTRIBUIDORA BEBIDAS SP"),
            ("22/06/2026", 800.00, "PIX RECEBIDO - SALAO VILLA FLORA"),
            ("25/06/2026", 350.00, "PIX ENVIADO - DOCES DA VO NINA"),
            ("28/06/2026", 1200.00, "PIX RECEBIDO - EMPRESA TECH SOLUTIONS"),
        ]
    elif slug == "novatech-ti":
        movs = [
            ("01/06/2026", 2500.00, "PIX RECEBIDO - AUTOPECAS LIMA"),
            ("02/06/2026", 4800.00, "PIX RECEBIDO - ROCHA & SILVA ADVOCACIA"),
            ("03/06/2026", 3200.00, "PIX RECEBIDO - FARMACIA BEM-ESTAR"),
            ("04/06/2026", 15000.00, "TED - FOLHA PAGAMENTO FUNCIONARIOS"),
            ("04/06/2026", 3500.00, "TED - ALUGUEL SALA TATUAPE"),
            ("05/06/2026", 3800.00, "PIX RECEBIDO - CONSTRUTORA NOVO NORTE"),
            ("07/06/2026", 12000.00, "PIX ENVIADO - DIGIDISTRI (ESTOQUE)"),
            ("08/06/2026", 600.00, "PIX RECEBIDO - MECANICA DO ZE"),
            ("10/06/2026", 9800.00, "PIX RECEBIDO - AUTOPECAS LIMA (HW EXTRA)"),
            ("12/06/2026", 1500.00, "PIX RECEBIDO - RESTAURANTE DO BETO"),
            ("14/06/2026", 900.00, "TED - CONTABILIDADE SR PAULO"),
            ("16/06/2026", 4200.00, "TED - AWS SERVICOS CLOUD"),
            ("18/06/2026", 500.00, "PIX RECEBIDO - DR FERNANDO"),
            ("20/06/2026", 200.00, "PIX RECEBIDO - BUFFET LUCIA'S FOOD"),
            ("22/06/2026", 850.00, "PIX ENVIADO - MERCADO LIVRE SUPRIMENTOS"),
            ("24/06/2026", 3400.00, "PIX RECEBIDO - FARMACIA BEM-ESTAR (EXTRA)"),
        ]

    # Nubank format
    nubank_path = os.path.join(base, f"extrato_nubank_{mes:02d}{ano}.csv")
    with open(nubank_path, "w", newline="", encoding="utf-8") as f:
        f.write('"Data","Valor","Identificador","Descricao"\n')
        saldo = round(random.uniform(3000, 12000), 2)
        for data, valor, desc in movs:
            ident = f"ID{random.randint(10000000, 99999999)}"
            f.write(f'"{data}",{valor:.2f},"{ident}","{desc}"\n')
            saldo += valor
    print(f"  ✓ Extrato Nubank: {nubank_path}")

    # Extrato Itaú (formato BR)
    itau_path = os.path.join(base, f"extrato_itau_{mes:02d}{ano}.csv")
    with open(itau_path, "w", newline="", encoding="utf-8") as f:
        f.write("Data Movimento;Código Histórico;Histórico;Valor;D/C;\n")
        for data, valor, desc in movs:
            hist_code = random.choice(["249", "301", "159", "135", "168"])
            dc = "C" if valor > 0 else "D"
            val_str = f"{abs(valor):.2f}".replace(".", ",")
            data_fmt = data.replace("/", "")
            f.write(f'"{data_fmt}";"{hist_code}";"{desc}";"{val_str}";"{dc}";\n')
    print(f"  ✓ Extrato Itaú: {itau_path}")


# ═══════════════════════════════════════════════════════════════════════════
# 4. CARDÁPIO — LÚCIA'S FOOD
# ═══════════════════════════════════════════════════════════════════════════

def gerar_cardapio_lucia():
    """Gera cardápio profissional PDF para Lúcia's Food (design da Carolina)."""
    base = os.path.join(PERSONAS_DIR, "lucia-buffet", "documentos-ruido")
    ensure_dir(base)

    pdf = DocPDF("Cardapio_Lucias_Food")
    pdf.add_page()

    # Capa
    pdf.set_fill_color(40, 30, 20)  # Marrom escuro (tema gastronômico)
    pdf.rect(0, 0, 210, 297, 'F')

    # Detalhe dourado
    pdf.set_draw_color(212, 175, 55)
    pdf.set_line_width(2)
    pdf.rect(20, 20, 170, 257)

    pdf.set_font("DejaVu", "B", 36)
    pdf.set_text_color(212, 175, 55)
    pdf.set_xy(20, 80)
    pdf.cell(170, 15, "LÚCIA'S FOOD", align="C")

    pdf.set_font("DejaVu", "", 14)
    pdf.set_text_color(200, 180, 150)
    pdf.set_xy(20, 100)
    pdf.cell(170, 10, "Buffet & Catering", align="C")

    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(180, 160, 130)
    pdf.set_xy(20, 115)
    pdf.cell(170, 8, "Desde 2014 | São Paulo - SP", align="C")

    # Linha decorativa
    pdf.set_draw_color(212, 175, 55)
    pdf.set_line_width(0.5)
    pdf.line(80, 130, 130, 130)

    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(180, 160, 130)
    pdf.set_xy(20, 140)
    pdf.cell(170, 8, "CARDÁPIO - EVENTOS SOCIAIS E CORPORATIVOS", align="C")

    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(212, 175, 55)
    pdf.set_xy(20, 200)
    pdf.cell(170, 6, "Design: Carolina Mendes Design", align="C")
    pdf.set_xy(20, 206)
    pdf.cell(170, 6, "Contato: (11) 9 9345-6789 | lucia@luciasfood.com.br", align="C")

    # Páginas internas
    pdf.add_page()
    pdf.set_fill_color(255, 252, 245)
    pdf.rect(0, 0, 210, 297, 'F')

    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(40, 30, 20)
    pdf.set_xy(15, 15)
    pdf.cell(0, 10, "ENTRADAS")
    pdf.set_draw_color(212, 175, 55)
    pdf.line(15, 27, 195, 27)

    entradas = [
        ("Bruschetta de Tomate Seco e Manjericão", "Pão italiano, tomate seco, queijo brie e manjericão fresco"),
        ("Carpaccio de Carne com Parmesão", "Carpaccio de maminha, lascas de parmesão, rúcula e molho mostarda"),
        ("Salada Caprese no Palito", "Tomate cereja, mussarela de búfala, manjericão e azeite balsâmico"),
        ("Pastelzinho de Camarão", "Massa crocante, recheio de camarão com catupiry"),
        ("Canapés de Salmão Defumado", "Pão preto, cream cheese, salmão defumado e endro"),
        ("Bolinhos de Bacalhau", "Bacalhau desfiado, batata, salsinha (receita da vó)"),
    ]
    y = 32
    for nome, desc in entradas:
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(60, 40, 20)
        pdf.set_xy(20, y)
        pdf.cell(0, 5, f"• {nome}")
        y += 5
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(100, 80, 60)
        pdf.set_xy(25, y)
        pdf.cell(0, 4, desc)
        y += 7

    # Segunda página — Pratos Principais
    pdf.add_page()
    pdf.set_fill_color(255, 252, 245)
    pdf.rect(0, 0, 210, 297, 'F')

    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(40, 30, 20)
    pdf.set_xy(15, 15)
    pdf.cell(0, 10, "PRATOS PRINCIPAIS")
    pdf.line(15, 27, 195, 27)

    pratos = [
        ("Filé Mignon ao Molho Madeira", "Filé mignon grelhado, molho madeira, arroz biro-biro e batata gratinada"),
        ("Salmão ao Molho de Maracujá", "Salmão grelhado, molho agridoce de maracujá, legumes salteados"),
        ("Risoto de Camarão ao Limão", "Arroz arbóreo, camarões grelhados, limão siciliano e salsinha"),
        ("Strogonoff de Frango Clássico", "Frango em cubos, molho de creme de leite, champignon e arroz branco"),
        ("Lasanha à Bolonhesa", "Massa artesanal, molho bolonhesa, queijos e bechamel"),
        ("Opção Vegana: Curry de Grão-de-Bico", "Grão-de-bico, leite de coco, curry, arroz basmati"),
    ]
    y = 32
    for nome, desc in pratos:
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(60, 40, 20)
        pdf.set_xy(20, y)
        pdf.cell(0, 5, f"• {nome}")
        y += 5
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(100, 80, 60)
        pdf.set_xy(25, y)
        pdf.cell(0, 4, desc)
        y += 7

    # Sobremesas
    y += 5
    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(40, 30, 20)
    pdf.set_xy(15, y)
    pdf.cell(0, 10, "SOBREMESAS")
    pdf.line(15, y + 12, 195, y + 12)
    y += 17
    sobremesas = [
        ("Petit Gâteau com Sorvete", "Bolo de chocolate com centro derretido, sorvete de creme"),
        ("Mousse de Maracujá", "Mousse aerado, calda de maracujá e chantilly"),
        ("Torta de Limão Siciliano", "Massa amanteigada, creme cítrico e merengue tostado"),
    ]
    for nome, desc in sobremesas:
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(60, 40, 20)
        pdf.set_xy(20, y)
        pdf.cell(0, 5, f"• {nome}")
        y += 5
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(100, 80, 60)
        pdf.set_xy(25, y)
        pdf.cell(0, 4, desc)
        y += 7

    path = os.path.join(base, "cardapio_lucias_food.pdf")
    pdf.output(path)
    print(f"  ✓ Cardápio PDF: {path}")


# ═══════════════════════════════════════════════════════════════════════════
# 5. MATERIAL DE DIVULGAÇÃO — FLYERS
# ═══════════════════════════════════════════════════════════════════════════

def gerar_flyer_carolina():
    """Flyer de portfólio / material de divulgação da Carolina."""
    base = os.path.join(PERSONAS_DIR, "carolina-design", "documentos-ruido", "divulgacao")
    ensure_dir(base)

    pdf = DocPDF("Flyer_Carolina_Design")
    pdf.add_page()

    # Fundo
    pdf.set_fill_color(245, 240, 255)
    pdf.rect(0, 0, 210, 297, 'F')

    # Logo area
    pdf.set_fill_color(80, 60, 140)
    pdf.rect(10, 10, 190, 40, 'F')
    pdf.set_font("DejaVu", "B", 24)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(10, 18)
    pdf.cell(190, 12, "CAROLINA MENDES DESIGN", align="C")
    pdf.set_font("DejaVu", "", 11)
    pdf.set_xy(10, 32)
    pdf.cell(190, 8, "Identidade Visual | Branding | Design Gráfico", align="C")

    # Portfolio cards
    cards = [
        ("IDENTIDADE VISUAL", "TechNova Sistemas", "R$ 28.000", "Manual de marca completo"),
        ("LOGO + CARDÁPIO", "Buffet Lúcia's Food", "R$ 2.500", "Cardápio digital + marca"),
        ("REDES SOCIAIS", "Estúdio Pilates Corpo Livre", "R$ 600/mês", "Gestão mensal de posts"),
        ("MATERIAL GRÁFICO", "Padaria Vitória", "R$ 1.800", "Folders, banners, cardápios"),
    ]
    y = 60
    for titulo, cliente, valor, desc in cards:
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(80, 60, 140)
        pdf.rect(15, y, 180, 35, style='DF')
        pdf.set_font("DejaVu", "B", 11)
        pdf.set_text_color(80, 60, 140)
        pdf.set_xy(20, y + 3)
        pdf.cell(0, 5, titulo)
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.set_xy(20, y + 11)
        pdf.cell(0, 4, f"Cliente: {cliente} | Valor: {valor}")
        pdf.set_xy(20, y + 17)
        pdf.cell(0, 4, desc)
        pdf.set_xy(20, y + 24)
        pdf.set_font("DejaVu", "", 7)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(0, 3, f"Ano: 2025-2026")
        y += 40

    # Depoimento
    y += 5
    pdf.set_fill_color(80, 60, 140)
    pdf.rect(15, y, 180, 30, 'F')
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, y + 3)
    pdf.multi_cell(170, 4,
        '"A Carolina transformou a identidade da minha empresa. '
        'O trabalho é impecável e a entrega foi no prazo." '
        '— João Nogueira, NovaTech TI')
    pdf.set_xy(20, y + 20)
    pdf.set_font("DejaVu", "", 7)
    pdf.cell(0, 4, "Contato: (11) 9 8765-4321 | carol@crmendes.design", align="C")

    path = os.path.join(base, "flyer_portfolio_carolina.pdf")
    pdf.output(path)
    print(f"  ✓ Flyer PDF (Carolina): {path}")


def gerar_flyer_novatech():
    """Flyer de serviços da NovaTech."""
    base = os.path.join(PERSONAS_DIR, "novatech-ti", "documentos-ruido", "divulgacao")
    ensure_dir(base)

    pdf = DocPDF("Flyer_NovaTech")
    pdf.add_page()

    pdf.set_fill_color(20, 50, 90)
    pdf.rect(0, 0, 210, 297, 'F')

    pdf.set_font("DejaVu", "B", 28)
    pdf.set_text_color(100, 180, 255)
    pdf.set_xy(10, 30)
    pdf.cell(190, 12, "NovaTech TI", align="C")
    pdf.set_font("DejaVu", "", 12)
    pdf.set_text_color(200, 220, 240)
    pdf.set_xy(10, 45)
    pdf.cell(190, 8, "Soluções em Tecnologia para sua Empresa", align="C")

    servicos = [
        ("🖥️ Suporte Técnico", "Manutenção preventiva e corretiva\nSuporte remoto e presencial\nContratos a partir de R$ 200/mês"),
        ("☁️ Nuvem e Infraestrutura", "Migração para Google Workspace\nServidores e armazenamento\nSegurança e backup"),
        ("🔧 Hardware", "Venda de equipamentos Dell, Intelbras\nRede estruturada (cabeamento, switch, WiFi)\nConsultoria de compra"),
        ("📊 Projetos Especiais", "Automação comercial\nSistemas PDV\nTreinamento de equipe"),
    ]

    y = 65
    for titulo, desc in servicos:
        pdf.set_fill_color(30, 60, 100)
        pdf.rect(15, y, 180, 35, 'F')
        pdf.set_font("DejaVu", "B", 12)
        pdf.set_text_color(100, 180, 255)
        pdf.set_xy(20, y + 3)
        pdf.cell(0, 5, titulo)
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(200, 210, 220)
        pdf.set_xy(20, y + 11)
        pdf.multi_cell(170, 4, desc)
        y += 42

    # Contato
    y = 260
    pdf.set_fill_color(30, 60, 100)
    pdf.rect(15, y, 180, 25, 'F')
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(200, 220, 240)
    pdf.set_xy(20, y + 3)
    pdf.cell(0, 4, "📞 (11) 9 8888-7777 | 📧 contato@novatechti.com.br")
    pdf.set_xy(20, y + 9)
    pdf.cell(0, 4, "📍 Rua Itapura, 1850, sala 307 - Tatuapé, SP")
    pdf.set_xy(20, y + 15)
    pdf.cell(0, 4, "CNPJ: 32.718.694/0001-07")

    path = os.path.join(base, "flyer_servicos_novatech.pdf")
    pdf.output(path)
    print(f"  ✓ Flyer PDF (NovaTech): {path}")


# ═══════════════════════════════════════════════════════════════════════════
# 6. CONTRATOS ASSINADOS
# ═══════════════════════════════════════════════════════════════════════════

def gerar_contrato_carolina_lucia():
    """Contrato entre Carolina e Lúcia (logo + cardápio) — assinado."""
    base = os.path.join(PERSONAS_DIR, "carolina-design", "documentos-ruido", "contratos")
    ensure_dir(base)

    pdf = DocPDF("Contrato_Carolina_Lucia")
    pdf.add_page()

    pdf.set_font("DejaVu", "B", 16)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, "CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE DESIGN", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, f"Data: 25 de maio de 2025", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Partes
    pdf.section_title("PARTES")
    pdf.section_body(
        "CONTRATADA: Carolina Mendes de Oliveira, CPF 384.029.170-50, MEI, "
        "estabelecida na Rua Artur de Azevedo, 1040, apto 72 - Pinheiros, SP.\n\n"
        "CONTRATANTE: Lúcia Alves Freitas ME (Lúcia's Food Buffet & Catering), "
        "CNPJ 48.792.305/0001-81, estabelecida na Rua Silva Teles, 332, sala 2 - Barra Funda, SP."
    )

    pdf.section_title("CLÁUSULA PRIMEIRA - OBJETO")
    pdf.section_body(
        "O presente contrato tem como objeto a prestação de serviços de design gráfico "
        "pela CONTRATADA à CONTRATANTE, compreendendo:\n"
        "  a) Criação de logotipo (3 propostas, 2 rodadas de ajustes);\n"
        "  b) Desenvolvimento de cardápio digital interativo;\n"
        "  c) Manual de aplicação da marca (6 páginas);\n"
        "  d) Arquivos finais em .ai, .eps, .pdf e .png."
    )

    pdf.section_title("CLÁUSULA SEGUNDA - VALOR E CONDIÇÕES")
    pdf.section_body(
        "O valor total dos serviços é de R$ 2.500,00 (dois mil e quinhentos reais), "
        "pagos da seguinte forma:\n"
        "  - 50% (R$ 1.250,00) no ato da assinatura (Pix);\n"
        "  - 50% (R$ 1.250,00) na entrega final.\n\n"
        "Forma de pagamento: Pix. Prazo de entrega: 15 dias úteis."
    )

    pdf.section_title("CLÁUSULA TERCEIRA - PRAZO E ENTREGA")
    pdf.section_body(
        "O prazo de execução é de 15 (quinze) dias úteis, contados da data de "
        "aprovação do briefing. A CONTRATADA se compromete a entregar os arquivos "
        "finais em formato editável e fechado."
    )

    pdf.section_title("DISPOSIÇÕES GERAIS")
    pdf.section_body(
        "Fica eleito o foro da Comarca de São Paulo para dirimir quaisquer "
        "dúvidas oriundas do presente contrato."
    )

    pdf.ln(10)
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, "São Paulo, 25 de maio de 2025", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.cell(80, 5, "___________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(80, 5, "Carolina Mendes de Oliveira", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.cell(80, 5, "___________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(80, 5, "Lúcia Alves Freitas", new_x="LMARGIN", new_y="NEXT")

    path = os.path.join(base, "contrato_carolina_lucia_assinado.pdf")
    pdf.output(path)
    print(f"  ✓ Contrato assinado: {path}")


def gerar_contrato_novatech_autopecas():
    """Contrato de manutenção NovaTech + AutoPeças Lima."""
    base = os.path.join(PERSONAS_DIR, "novatech-ti", "documentos-ruido", "contratos")
    ensure_dir(base)

    pdf = DocPDF("Contrato_NovaTech_AutoPecas")
    pdf.add_page()

    pdf.set_font("DejaVu", "B", 16)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, "CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE TI", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, "Contrato nº: NT-2019-001", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Data: 15 de janeiro de 2019 (Renovado automaticamente)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.section_title("PARTES")
    pdf.section_body(
        "CONTRATADA: NovaTech Soluções em Informática Ltda., CNPJ 32.718.694/0001-07, "
        "Rua Itapura, 1850, sala 307 - Tatuapé, São Paulo/SP.\n\n"
        "CONTRATANTE: AutoPeças Lima Ltda., CNPJ 11.222.333/0001-44, "
        "Av. Celso Garcia, 4500 - Belenzinho, São Paulo/SP."
    )

    pdf.section_title("CLÁUSULA PRIMEIRA - OBJETO")
    pdf.section_body(
        "Prestação de serviços de manutenção preventiva e corretiva de equipamentos "
        "de informática, compreendendo:\n"
        "  a) Suporte técnico remoto e presencial para 20 (vinte) estações de trabalho;\n"
        "  b) Manutenção preventiva mensal;\n"
        "  c) Backup semanal dos dados do servidor;\n"
        "  d) Atendimento emergencial em até 4 horas úteis."
    )

    pdf.section_title("CLÁUSULA SEGUNDA - VALOR E REAJUSTE")
    pdf.section_body(
        "Valor mensal: R$ 2.500,00 (dois mil e quinhentos reais).\n"
        "Pagamento: boleto bancário, todo dia 10 do mês.\n"
        "Reajuste: anual pelo IPCA.\n"
        "Peças e hardware necessários para reparo serão cobrados à parte "
        "mediante orçamento prévio."
    )

    pdf.section_title("CLÁUSULA TERCEIRA - PRAZO")
    pdf.section_body(
        "Prazo mínimo: 12 meses. Renovação automática por igual período.\n"
        "Rescisão: comunicação com 30 dias de antecedência.\n"
        "Multa rescisória: 20% sobre o saldo do contrato."
    )

    pdf.ln(10)
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, "São Paulo, 15 de janeiro de 2019", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.cell(80, 5, "___________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(80, 5, "___________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(80, 5, "João Nogueira - NovaTech TI", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(80, 5, "Seu Lima - AutoPeças Lima", new_x="LMARGIN", new_y="NEXT")

    path = os.path.join(base, "contrato_novatech_autopecas_assinado.pdf")
    pdf.output(path)
    print(f"  ✓ Contrato assinado: {path}")


# ═══════════════════════════════════════════════════════════════════════════
# 7. PROPOSTAS ANTIGAS DETALHADAS
# ═══════════════════════════════════════════════════════════════════════════

def gerar_proposta_antiga_carolina():
    """Proposta antiga da Carolina — projeto TechNova."""
    base = os.path.join(PERSONAS_DIR, "carolina-design", "documentos-ruido", "propostas_antigas")
    ensure_dir(base)

    pdf = DocPDF("Proposta_TechNova")
    pdf.add_page()

    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, "PROPOSTA COMERCIAL", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 5, "Proposta nº: PC-2024-008 | Data: 10 de fevereiro de 2024", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Validade: 15 dias", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.section_title("PARA")
    pdf.section_body("TechNova Sistemas Ltda. | CNPJ: 33.444.555/0001-66\nContato: Procurement | compras@technova.com.br")

    pdf.section_title("PROJETO: IDENTIDADE VISUAL COMPLETA")
    pdf.section_body(
        "Escopo do projeto:\n"
        "  1. Briefing e pesquisa de mercado\n"
        "  2. Criação de 3 propostas de logotipo\n"
        "  3. Refinamento (até 3 rodadas)\n"
        "  4. Manual da marca (20 páginas)\n"
        "  5. Aplicações: cartão, papelaria, assinatura de e-mail\n"
        "  6. Killer Pack: arquivos .ai, .eps, .pdf, .png\n\n"
        "Valor total: R$ 28.000,00 (vinte e oito mil reais)\n"
        "Forma de pagamento: 3 parcelas de R$ 9.333,33\n"
        "  - 1ª parcela: assinatura (R$ 9.333,33)\n"
        "  - 2ª parcela: aprovação do logo (R$ 9.333,33)\n"
        "  - 3ª parcela: entrega final (R$ 9.333,34)\n\n"
        "Prazo de execução: 45 dias úteis.\n"
        "ISS: 5% (NFSe emitida pela prestadora - MEI)."
    )

    pdf.section_title("CONDIÇÕES GERAIS")
    pdf.section_body(
        "- 3 rodadas de ajustes inclusas no valor\n"
        "- Após aprovação final, 30 dias de suporte para dúvidas\n"
        "- Arquivos fontes (editáveis) liberados somente após último pagamento\n"
        "- Não inclui registro de marca no INPI"
    )

    pdf.ln(5)
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, "___________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Carolina Mendes de Oliveira", new_x="LMARGIN", new_y="NEXT")

    path = os.path.join(base, "proposta_technova_28000.pdf")
    pdf.output(path)
    print(f"  ✓ Proposta antiga (Carolina): {path}")


def gerar_proposta_construtora():
    """Proposta da NovaTech para Construtora Novo Norte - migração nuvem."""
    base = os.path.join(PERSONAS_DIR, "novatech-ti", "documentos-ruido", "propostas_antigas")
    ensure_dir(base)

    pdf = DocPDF("Proposta_NovoNorte_Nuvem")
    pdf.add_page()

    pdf.set_font("DejaVu", "B", 16)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 10, "PROPOSTA TÉCNICO-COMERCIAL", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 5, "Proposta nº: NT-CNN-2026-001 | Data: 15 de janeiro de 2026", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.section_title("CLIENTE")
    pdf.section_body("Construtora Novo Norte Ltda. | CNPJ: 22.456.789/0001-10\nContato: Eng. Carlos | (11) 9 7777-8888")

    pdf.section_title("OBJETO: MIGRAÇÃO PARA NUVEM - 30 ESTAÇÕES")
    pdf.section_body(
        "Escopo completo:\n\n"
        "1. INFRAESTRUTURA\n"
        "   - Migração de servidor local para Google Workspace Business\n"
        "   - Configuração de 30 contas de e-mail profissionais\n"
        "   - Migração de arquivos (aproximadamente 1.2TB) para Google Drive\n"
        "   - Configuração de segurança e MFA\n\n"
        "2. REDE\n"
        "   - Substituição do switch (modelo Intelbras 24 portas)\n"
        "   - Novo roteador com VPN para acesso remoto\n"  
        "   - Cabeamento estruturado nos 3 andares\n\n"
        "3. TREINAMENTO\n"
        "   - Workshop de 4h para equipe (ferramentas Google)\n"
        "   - Manual do usuário personalizado\n"
        "   - Suporte por 30 dias pós-migração\n\n"
        "VALOR TOTAL: R$ 45.000,00 (quarenta e cinco mil reais)"
    )

    pdf.section_title("CRONOGRAMA")
    pdf.section_body(
        "Semana 1: Diagnóstico e preparação do ambiente\n"
        "Semana 2: Migração de e-mails e dados\n"
        "Semana 3: Configuração de rede e segurança\n"
        "Semana 4: Testes, treinamento e Go-Live\n\n"
        "Equipe alocada: João Nogueira (sênior) + Rafael Oliveira (pleno)\n"
        "Prazo total: 21 dias úteis"
    )

    pdf.section_title("CONDIÇÕES DE PAGAMENTO")
    pdf.section_body(
        "50% na assinatura: R$ 22.500,00\n"
        "25% na conclusão da migração: R$ 11.250,00\n"
        "25% após Go-Live e aceitação: R$ 11.250,00\n\n"
        "Garantia de 90 dias sobre os serviços prestados.\n"
        "Equipamentos: garantia do fabricante (1-3 anos)."
    )

    path = os.path.join(base, "proposta_construtora_nuvem_45000.pdf")
    pdf.output(path)
    print(f"  ✓ Proposta técnica (NovaTech): {path}")


# ═══════════════════════════════════════════════════════════════════════════
# 8. PROPAGANDA / FLYER LÚCIA
# ═══════════════════════════════════════════════════════════════════════════

def gerar_flyer_lucia():
    """Flyer de divulgação do Buffet Lúcia's Food."""
    base = os.path.join(PERSONAS_DIR, "lucia-buffet", "documentos-ruido", "divulgacao")
    ensure_dir(base)

    pdf = DocPDF("Flyer_Lucias_Food")
    pdf.add_page()

    # Fundo escuro elegante
    pdf.set_fill_color(30, 25, 20)
    pdf.rect(0, 0, 210, 297, 'F')

    pdf.set_font("DejaVu", "B", 26)
    pdf.set_text_color(212, 175, 55)
    pdf.set_xy(10, 40)
    pdf.cell(190, 12, "LÚCIA'S FOOD", align="C")
    pdf.set_font("DejaVu", "", 12)
    pdf.set_text_color(200, 180, 150)
    pdf.set_xy(10, 55)
    pdf.cell(190, 8, "Buffet & Catering desde 2014", align="C")

    # Serviços
    pdf.set_fill_color(50, 40, 30)
    svcs = [
        "🍽️ Casamentos e Festas",
        "☕ Coffee Breaks Corporativos",
        "🎂 Aniversários e 15 Anos",
        "🥗 Marmitas Executivas",
        "🎄 Confraternizações",
    ]
    y = 80
    for s in svcs:
        pdf.rect(25, y, 160, 14, 'F')
        pdf.set_font("DejaVu", "", 11)
        pdf.set_text_color(212, 175, 55)
        pdf.set_xy(30, y + 2)
        pdf.cell(0, 8, s)
        y += 18

    # Diferenciais
    y += 10
    pdf.set_font("DejaVu", "B", 12)
    pdf.set_text_color(200, 180, 150)
    pdf.set_xy(10, y)
    pdf.cell(190, 8, "DIFERENCIAIS", align="C")
    y += 12
    diffs = [
        "✓ Atendimento personalizado",
        "✓ Cardápio adaptável (opções veganas, restrições)",
        "✓ Equipe profissional e uniformizada",
        "✓ Cozinha própria na Barra Funda",
        "✓ Mais de 300 eventos realizados",
    ]
    for d in diffs:
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(180, 170, 150)
        pdf.set_xy(25, y)
        pdf.cell(0, 6, d)
        y += 7

    # Contato
    y = 260
    pdf.set_fill_color(50, 40, 30)
    pdf.rect(15, y, 180, 25, 'F')
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(212, 175, 55)
    pdf.set_xy(20, y + 3)
    pdf.cell(0, 4, "📞 (11) 9 9345-6789 | 📧 lucia@luciasfood.com.br")
    pdf.set_xy(20, y + 9)
    pdf.cell(0, 4, "📍 Rua Silva Teles, 332 - Barra Funda, SP")
    pdf.set_xy(20, y + 15)
    pdf.cell(0, 4, "📷 @luciasfoodbuffet (Instagram)")

    path = os.path.join(base, "flyer_lucias_food.pdf")
    pdf.output(path)
    print(f"  ✓ Flyer PDF (Lúcia): {path}")


# ═══════════════════════════════════════════════════════════════════════════
# 9. IMAGEM DE MARCA D'ÁGUA / LOGO PLACEHOLDER
# ═══════════════════════════════════════════════════════════════════════════

def gerar_placeholder_logo(slug, nome, cor):
    """Gera uma imagem PNG placeholder de logo."""
    base = os.path.join(PERSONAS_DIR, slug, "documentos-ruido", "imagens")
    ensure_dir(base)

    if not HAS_PIL:
        return

    img = Image.new('RGB', (200, 100), color=cor)
    draw = ImageDraw.Draw(img)

    # Texto centralizado
    try:
        font = ImageFont.truetype("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf", 16)
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), nome, font=font)
    tw = bbox[2] - bbox[0]
    x = (200 - tw) // 2
    draw.text((x, 40), nome, fill=(255, 255, 255), font=font)

    # Linha decorativa
    draw.line([(40, 65), (160, 65)], fill=(255, 255, 255), width=2)

    path = os.path.join(base, f"logo_placeholder_{slug}.png")
    img.save(path)
    print(f"  ✓ Logo placeholder: {path}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("GERADOR DE DOCUMENTOS RICOS — PERSONAS BLU")
    print("=" * 60)

    # Extratos bancários para todas as personas
    print("\n📊 Gerando extratos bancários...")
    gerar_extrato_nubank("Carolina Mendes", "carolina-design", "384.029.170-50")
    gerar_extrato_nubank("Lúcia Alves Freitas", "lucia-buffet", "48.792.305/0001-81")
    gerar_extrato_nubank("NovaTech TI", "novatech-ti", "32.718.694/0001-07")

    # NFs escaneadas
    print("\n📄 Gerando NFs escaneadas (DANFE/NFSe)...")
    gerar_nfse_carolina()
    gerar_danfe_lucia()
    gerar_danfe_novatech()

    # Cardápio
    print("\n🍽️ Gerando cardápio...")
    gerar_cardapio_lucia()

    # Material de divulgação
    print("\n📢 Gerando materiais de divulgação...")
    gerar_flyer_carolina()
    gerar_flyer_novatech()
    gerar_flyer_lucia()

    # Contratos assinados
    print("\n📝 Gerando contratos assinados...")
    gerar_contrato_carolina_lucia()
    gerar_contrato_novatech_autopecas()

    # Propostas antigas
    print("\n📋 Gerando propostas antigas...")
    gerar_proposta_antiga_carolina()
    gerar_proposta_construtora()

    # Logos placeholder
    print("\n🖼️ Gerando imagens placeholder...")
    gerar_placeholder_logo("carolina-design", "CAROLINA DESIGN", (80, 60, 140))
    gerar_placeholder_logo("lucia-buffet", "LUCIAS FOOD", (40, 30, 20))
    gerar_placeholder_logo("novatech-ti", "NOVATECH TI", (20, 50, 90))

    print(f"\n{'='*60}")
    print("GERAÇÃO CONCLUÍDA!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
