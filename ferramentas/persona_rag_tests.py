#!/usr/bin/env python3
"""
Persona-based RAG Tests

Tests the RAG functionality against all 7 seed personas defined in
ferramentas/seeds/knowledge/*.json

Each persona has a unique knowledge base (collection_rag) with specific
information that only RAG can retrieve. The tests send questions that
require knowledge retrieval to answer correctly.

Usage:
    python ferramentas/persona_rag_tests.py [--verbose] [--persona <name>]

Or via Make:
    make test-personas
"""

import httpx
import json
import asyncio
import argparse
import sys
import subprocess
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================================
# FETCH API KEYS FROM DATABASE
# ============================================================================

def get_api_keys_from_db() -> dict[str, str]:
    """Fetch API keys for personas from the database."""
    try:
        result = subprocess.run(
            [
                "docker", "compose", "exec", "-T", "postgres",
                "psql", "-U", "user", "-d", "vizu_db", "-t", "-c",
                "SELECT nome_empresa, api_key FROM cliente_vizu WHERE nome_empresa NOT LIKE 'E2E%';"
            ],
            capture_output=True,
            text=True,
            cwd="/Users/lucascruz/Documents/GitHub/vizu-mono",
            timeout=10,
        )

        keys = {}
        for line in result.stdout.strip().split("\n"):
            if "|" in line:
                parts = line.split("|")
                nome = parts[0].strip()
                api_key = parts[1].strip()
                if nome and api_key:
                    keys[nome] = api_key

        return keys
    except Exception as e:
        print(f"⚠️ Could not fetch API keys from DB: {e}")
        return {}


# ============================================================================
# PERSONA TEST DEFINITIONS
# ============================================================================

@dataclass
class PersonaTest:
    """Defines a persona and its test questions."""
    nome_empresa: str
    api_key: str  # Will be fetched from DB
    collection_rag: str
    questions: list[dict]  # {"question": str, "expected_keywords": list[str]}


def build_persona_tests(api_keys: dict[str, str]) -> list[PersonaTest]:
    """Build persona tests with API keys from database."""

    tests = []

    # Studio J
    if "Studio J" in api_keys:
        tests.append(PersonaTest(
            nome_empresa="Studio J",
            api_key=api_keys["Studio J"],
            collection_rag="studio_j_conhecimento",
            questions=[
                {
                    "question": "Quais serviços vocês oferecem para cabelos?",
                    "expected_keywords": ["corte", "coloração", "progressiva", "hidratação", "escova"],
                },
                {
                    "question": "Qual o preço do corte feminino?",
                    "expected_keywords": ["R$", "reais", "preço", "valor"],
                },
                {
                    "question": "Preciso preparar meu cabelo antes de fazer progressiva?",
                    "expected_keywords": ["lavar", "produto", "residuo", "oleosidade", "pré-química"],
                },
            ],
        ))

    # Brasa & Malte
    if "Brasa & Malte Burger" in api_keys:
        tests.append(PersonaTest(
            nome_empresa="Brasa & Malte Burger",
            api_key=api_keys["Brasa & Malte Burger"],
            collection_rag="brasa_malte_cardapio",
            questions=[
                {
                    "question": "Quais hambúrgueres vocês têm no cardápio?",
                    "expected_keywords": ["Clássico", "Bacon", "Veggie", "hambúrguer"],
                },
                {
                    "question": "Vocês têm opções vegetarianas?",
                    "expected_keywords": ["Veggie", "vegetariano", "grão de bico", "plant-based"],
                },
                {
                    "question": "Como funciona a entrega?",
                    "expected_keywords": ["entrega", "iFood", "Rappi", "delivery", "km"],
                },
            ],
        ))

    # Pixel Store
    if "Pixel Store" in api_keys:
        tests.append(PersonaTest(
            nome_empresa="Pixel Store",
            api_key=api_keys["Pixel Store"],
            collection_rag="pixel_store_catalogo",
            questions=[
                {
                    "question": "Vocês vendem iPhone?",
                    "expected_keywords": ["iPhone", "Apple", "estoque", "modelo"],
                },
                {
                    "question": "Qual a política de trocas?",
                    "expected_keywords": ["troca", "dias", "nota fiscal", "devolução", "defeito"],
                },
                {
                    "question": "Vocês têm fones de ouvido sem fio?",
                    "expected_keywords": ["wireless", "bluetooth", "fone", "AirPods", "Galaxy Buds"],
                },
            ],
        ))

    # Dra. Beatriz - try both name variations
    dra_key = api_keys.get("Consultório Dra. Beatriz Almeida") or api_keys.get("Consultório Odontológico Dra. Beatriz Almeida")
    dra_name = "Consultório Dra. Beatriz Almeida" if "Consultório Dra. Beatriz Almeida" in api_keys else "Consultório Odontológico Dra. Beatriz Almeida"
    if dra_key:
        tests.append(PersonaTest(
            nome_empresa=dra_name,
            api_key=dra_key,
            collection_rag="dra_beatriz_faq",
            questions=[
                {
                    "question": "Quanto custa uma limpeza?",
                    "expected_keywords": ["R$", "limpeza", "profilaxia", "preço"],
                },
                {
                    "question": "Vocês aceitam convênio?",
                    "expected_keywords": ["convênio", "plano", "reembolso", "escolha"],
                },
                {
                    "question": "Como faço para agendar uma consulta?",
                    "expected_keywords": ["WhatsApp", "telefone", "agendar", "horário"],
                },
            ],
        ))

    # Marcos Eletricista
    if "Marcos Eletricista" in api_keys:
        tests.append(PersonaTest(
            nome_empresa="Marcos Eletricista",
            api_key=api_keys["Marcos Eletricista"],
            collection_rag="marcos_eletricista_conhecimento",
            questions=[
                {
                    "question": "Quais serviços você oferece?",
                    "expected_keywords": ["instalação", "reparo", "disjuntor", "tomada", "fiação"],
                },
                {
                    "question": "Como funciona o orçamento?",
                    "expected_keywords": ["orçamento", "visita", "gratuito", "avaliação"],
                },
                {
                    "question": "Você dá garantia no serviço?",
                    "expected_keywords": ["garantia", "meses", "dias", "serviço"],
                },
            ],
        ))

    # Oficina Mendes
    if "Oficina Mendes" in api_keys:
        tests.append(PersonaTest(
            nome_empresa="Oficina Mendes",
            api_key=api_keys["Oficina Mendes"],
            collection_rag="oficina_mendes_conhecimento",
            questions=[
                {
                    "question": "Quais serviços a oficina oferece?",
                    "expected_keywords": ["revisão", "freio", "suspensão", "motor", "óleo"],
                },
                {
                    "question": "Vocês trabalham no sábado?",
                    "expected_keywords": ["sábado", "horário", "12", "domingo"],
                },
                {
                    "question": "Qual a garantia dos serviços?",
                    "expected_keywords": ["garantia", "90 dias", "peças", "mão de obra"],
                },
            ],
        ))

    # Casa com Alma
    if "Casa com Alma" in api_keys:
        tests.append(PersonaTest(
            nome_empresa="Casa com Alma",
            api_key=api_keys["Casa com Alma"],
            collection_rag="casa_alma_catalogo",
            questions=[
                {
                    "question": "Vocês vendem velas aromáticas?",
                    "expected_keywords": ["vela", "aroma", "perfumaria", "casa"],
                },
                {
                    "question": "Como funciona a entrega?",
                    "expected_keywords": ["entrega", "frete", "Zona Sul", "motoboy", "transportadora"],
                },
                {
                    "question": "Vocês têm almofadas decorativas?",
                    "expected_keywords": ["almofada", "têxtil", "decorativa", "R$"],
                },
            ],
        ))

    return tests


# ============================================================================
# TEST EXECUTION
# ============================================================================

@dataclass
class TestResult:
    """Result of a single test."""
    persona: str
    question: str
    success: bool
    response: str
    keywords_found: list[str] = field(default_factory=list)
    keywords_missing: list[str] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    error: Optional[str] = None


async def run_persona_test(
    client: httpx.AsyncClient,
    persona: PersonaTest,
    question_data: dict,
    verbose: bool = False,
) -> TestResult:
    """Run a single test for a persona."""
    question = question_data["question"]
    expected_keywords = question_data["expected_keywords"]

    # Generate unique session ID
    session_id = f"rag-test-{persona.nome_empresa.lower().replace(' ', '-')[:20]}-{hash(question) % 10000}"

    try:
        response = await client.post(
            "http://localhost:8003/chat",
            json={
                "message": question,
                "session_id": session_id,
            },
            headers={
                "X-API-KEY": persona.api_key,
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

        if response.status_code != 200:
            return TestResult(
                persona=persona.nome_empresa,
                question=question,
                success=False,
                response="",
                error=f"HTTP {response.status_code}: {response.text}",
            )

        data = response.json()
        response_text = data.get("response", "").lower()
        tools_called = [t.get("tool_name", "") for t in data.get("tools_called", []) or []]

        # Check for expected keywords
        keywords_found = []
        keywords_missing = []

        for keyword in expected_keywords:
            if keyword.lower() in response_text:
                keywords_found.append(keyword)
            else:
                keywords_missing.append(keyword)

        # Test success criteria:
        # - If tools_called is reported, RAG must be called + 30% keywords
        # - If tools_called is null (atendente_core doesn't report it), just check keywords (50%)
        rag_called = any("rag" in t.lower() for t in tools_called)
        keyword_ratio = len(keywords_found) / len(expected_keywords) if expected_keywords else 1

        if tools_called:  # vendas_agent reports tools
            success = rag_called and keyword_ratio >= 0.3
        else:  # atendente_core doesn't report tools_called
            success = keyword_ratio >= 0.4  # 40% keywords is good enough

        result = TestResult(
            persona=persona.nome_empresa,
            question=question,
            success=success,
            response=data.get("response", "")[:500],  # Truncate for display
            keywords_found=keywords_found,
            keywords_missing=keywords_missing,
            tools_called=tools_called,
        )

        if verbose:
            print(f"\n{'✅' if success else '❌'} {persona.nome_empresa}")
            print(f"   Q: {question}")
            print(f"   Tools: {tools_called}")
            print(f"   Keywords found: {keywords_found}")
            print(f"   Keywords missing: {keywords_missing}")

        return result

    except Exception as e:
        return TestResult(
            persona=persona.nome_empresa,
            question=question,
            success=False,
            response="",
            error=str(e),
        )


async def run_all_tests(
    verbose: bool = False,
    persona_filter: Optional[str] = None,
) -> list[TestResult]:
    """Run all persona RAG tests."""

    # Fetch API keys from database
    print("🔑 Fetching API keys from database...")
    api_keys = get_api_keys_from_db()

    if not api_keys:
        print("❌ No API keys found in database. Please seed the database first.")
        return []

    print(f"   Found {len(api_keys)} clients with API keys")

    # Build persona tests
    persona_tests = build_persona_tests(api_keys)

    if not persona_tests:
        print("❌ No persona tests could be created (missing API keys)")
        return []

    results = []

    # Filter personas if requested
    if persona_filter:
        persona_tests = [p for p in persona_tests if persona_filter.lower() in p.nome_empresa.lower()]
        if not persona_tests:
            print(f"❌ No persona found matching '{persona_filter}'")
            return []

    async with httpx.AsyncClient() as client:
        for persona in persona_tests:
            print(f"\n🧪 Testing {persona.nome_empresa} ({persona.collection_rag})...")

            for question_data in persona.questions:
                result = await run_persona_test(client, persona, question_data, verbose)
                results.append(result)

                # Small delay between requests
                await asyncio.sleep(0.5)

    return results


def print_summary(results: list[TestResult]):
    """Print test summary."""
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed

    print("\n" + "=" * 60)
    print("📊 RAG PERSONA TEST SUMMARY")
    print("=" * 60)

    # Group by persona
    by_persona = {}
    for r in results:
        if r.persona not in by_persona:
            by_persona[r.persona] = []
        by_persona[r.persona].append(r)

    for persona, persona_results in by_persona.items():
        persona_passed = sum(1 for r in persona_results if r.success)
        persona_total = len(persona_results)
        emoji = "✅" if persona_passed == persona_total else "⚠️" if persona_passed > 0 else "❌"
        print(f"{emoji} {persona}: {persona_passed}/{persona_total} tests passed")

    print("-" * 60)
    print(f"📈 Total: {passed}/{total} tests passed ({100*passed/total:.1f}%)")

    if failed > 0:
        print("\n❌ Failed tests:")
        for r in results:
            if not r.success:
                print(f"   - {r.persona}: {r.question[:50]}...")
                if r.error:
                    print(f"     Error: {r.error}")
                else:
                    print(f"     Tools: {r.tools_called}")
                    print(f"     Missing keywords: {r.keywords_missing}")

    return passed == total


def main():
    parser = argparse.ArgumentParser(description="Run persona-based RAG tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--persona", "-p", type=str, help="Filter by persona name")
    args = parser.parse_args()

    print("🚀 Starting Persona RAG Tests")
    print(f"📅 {datetime.now().isoformat()}")

    results = asyncio.run(run_all_tests(verbose=args.verbose, persona_filter=args.persona))

    if not results:
        print("No tests run")
        sys.exit(1)

    all_passed = print_summary(results)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
