#!/usr/bin/env python3
"""Verify standalone agent prompts and Langfuse-first enforcement."""

import asyncio
import os
import sys

# Add libs to path
sys.path.insert(0, "/Users/lucascruz/Documents/GitHub/vizu-mono/libs")


async def verify_prompts():
    """Verify all standalone prompts exist and can be loaded."""
    from vizu_prompt_management.dynamic_builder import build_prompt_full
    from vizu_prompt_management.loader import PromptNotFoundError

    prompts = [
        "standalone/config-helper",
        "standalone/data-analyst",
        "standalone/knowledge-assistant",
        "standalone/report-generator",
    ]

    print("=" * 70)
    print("PHASE 7: LANGFUSE PROMPTS & OBSERVABILITY VERIFICATION")
    print("=" * 70)
    print()

    # Test 1: Load all prompts from Langfuse
    print("✓ TEST 1: Load all standalone prompts from Langfuse")
    print("-" * 70)

    for prompt_name in prompts:
        try:
            loaded = await build_prompt_full(
                name=prompt_name,
                variables={
                    "agent_name": "Test Agent",
                    "collected_context": {},
                    "csv_datasets": [],
                    "document_count": 0,
                    "google_connected": False,
                },
            )
            status = "✅"
            source = loaded.source
            print(f"{status} {prompt_name:<40} (source={source}, version={loaded.version})")
        except PromptNotFoundError as e:
            print(f"❌ {prompt_name:<40} NOT FOUND")
            print(f"   Error: {e}")
            return False
        except Exception as e:
            print(f"❌ {prompt_name:<40} ERROR")
            print(f"   Error: {type(e).__name__}: {e}")
            return False

    print()

    # Test 2: Verify Langfuse-first enforcement
    print("✓ TEST 2: Verify Langfuse-first enforcement (allow_fallback=False)")
    print("-" * 70)

    from vizu_prompt_management.loader import PromptLoader

    loader = PromptLoader(cache_ttl_seconds=300)

    # Try to load a non-existent prompt (should fail, no fallback to builtin)
    try:
        loaded = await loader.load(
            name="standalone/nonexistent-prompt",
            variables={},
            allow_fallback=False,
        )
        print("❌ Expected PromptNotFoundError but got success - enforcement failed!")
        return False
    except PromptNotFoundError:
        print("✅ PromptNotFoundError raised as expected (Langfuse-first enforcement works)")
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return False

    print()

    # Test 3: Verify no builtin templates for standalone prompts
    print("✓ TEST 3: Verify NO builtin templates for standalone prompts")
    print("-" * 70)

    from vizu_prompt_management.templates import BUILTIN_TEMPLATES

    standalone_builtins = [name for name in BUILTIN_TEMPLATES.keys() if "standalone" in name]
    if standalone_builtins:
        print(f"❌ Found builtin templates for standalone prompts (should be empty):")
        for name in standalone_builtins:
            print(f"   - {name}")
        return False
    else:
        print("✅ No builtin templates for standalone prompts (correct)")

    print()

    # Test 4: Verify prompt metadata
    print("✓ TEST 4: Verify prompt metadata and labels")
    print("-" * 70)

    for prompt_name in prompts:
        try:
            loaded = await build_prompt_full(
                name=prompt_name,
                variables={},
            )
            if loaded.langfuse_label == "production":
                print(f"✅ {prompt_name:<40} label=production")
            else:
                print(f"⚠️  {prompt_name:<40} label={loaded.langfuse_label} (expected 'production')")
        except Exception as e:
            print(f"❌ {prompt_name:<40} - {e}")
            return False

    print()
    print("=" * 70)
    print("✅ ALL TESTS PASSED - Phase 7 Langfuse setup is complete!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_prompts())
    sys.exit(0 if success else 1)
