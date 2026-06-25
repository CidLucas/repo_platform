// Deno test for supabase/functions/onboarding-website-intel/index.ts
//
// AC#12 — RED: the `await fetch(normalized, ...)` call inside
// `Deno.serve` must be wrapped in a `try { ... } catch (...) { ... } finally { ... }`
// whose `catch` handler returns `confidence: 0.35` (NOT `0`).
//
// Run with:
//   deno test --allow-read supabase/functions/onboarding-website-intel/index_test.ts
//
// Strategy: source inspection. We read the .ts file as text and locate the
// `try {` that immediately precedes `await fetch(normalized,`. We then
// walk the brace structure to find the matching closing `}` of that `try`,
// and finally inspect what follows — it MUST be a `catch` clause (not
// `finally` only), and the catch body MUST contain `confidence: 0.35` and
// MUST NOT contain the top-level `confidence: 0`.
//
// This is deliberately offline (no module import, no `Deno.serve` listener)
// so the test is deterministic and cannot be flaky on CI.
//
// RED state at current HEAD (pr-200-bkl-019 @ 4ca47da3):
//   index.ts has `try { ... await fetch(...) ... } finally { clearTimeout(...) }`
//   with NO `catch` clause. The error propagates to the outer `try { ... }
//   catch (err) { ... confidence: 0.35 }` (a different, wider scope). Per
//   AC#12, the fetch must own its own `catch` returning `confidence: 0.35`.

import {
  assert,
  assertEquals,
  assertStringIncludes,
} from "https://deno.land/std@0.224.0/assert/mod.ts";

const INDEX_TS_PATH = new URL("./index.ts", import.meta.url);

function readIndexSource(): string {
  return Deno.readTextFileSync(INDEX_TS_PATH);
}

interface FetchTryAnalysis {
  tryBlockStart: number;
  tryBlockEnd: number;
  afterTry: string;
  hasCatch: boolean;
  catchBody: string | null;
  hasFinally: boolean;
}

function analyzeFetchTry(source: string): FetchTryAnalysis | null {
  const fetchIdx = source.indexOf("await fetch(normalized,");
  if (fetchIdx === -1) return null;

  const before = source.slice(0, fetchIdx);
  const tryStart = before.lastIndexOf("try {");
  if (tryStart === -1) return null;

  let depth = 0;
  let tryEnd = -1;
  for (let i = tryStart; i < source.length; i++) {
    const ch = source[i];
    if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) {
        tryEnd = i;
        break;
      }
    }
  }
  if (tryEnd === -1) return null;

  const afterTry = source.slice(tryEnd + 1);

  const catchOpenMatch = afterTry.match(/^\s*catch\s*(?:\([^)]*\))?\s*\{/);
  const hasCatch = catchOpenMatch !== null;
  let catchBody: string | null = null;

  if (hasCatch && catchOpenMatch.index !== undefined) {
    const catchBodyStart = catchOpenMatch.index + catchOpenMatch[0].length;
    let cDepth = 1;
    let catchEnd = -1;
    for (let i = catchBodyStart; i < afterTry.length; i++) {
      const ch = afterTry[i];
      if (ch === "{") cDepth++;
      else if (ch === "}") {
        cDepth--;
        if (cDepth === 0) {
          catchEnd = i;
          break;
        }
      }
    }
    if (catchEnd !== -1) {
      catchBody = afterTry.slice(catchBodyStart, catchEnd);
    }
  }

  const finallyMatch = afterTry.match(
    /^\s*(?:catch\s*(?:\([^)]*\))?\s*\{[\s\S]*?\}\s*)?finally\s*\{/,
  );
  const hasFinally = finallyMatch !== null;

  return {
    tryBlockStart: tryStart,
    tryBlockEnd: tryEnd,
    afterTry,
    hasCatch,
    catchBody,
    hasFinally,
  };
}

Deno.test({
  name: "AC#12 RED — fetch catch returns confidence 0.35 (not 0)",
  fn: () => {
    const source = readIndexSource();

    assertStringIncludes(
      source,
      "await fetch(normalized,",
      "Sanity: index.ts must contain the `await fetch(normalized, ...)` call.",
    );

    const analysis = analyzeFetchTry(source);
    assert(
      analysis !== null,
      "Could not locate the `try {` block that wraps `await fetch(normalized, ...)`.",
    );

    // AC#12 — the fetch's try block MUST have a catch clause.
    assertEquals(
      analysis!.hasCatch,
      true,
      "AC#12 RED — the `try { ... await fetch(normalized, ...) ... }` block in " +
        "supabase/functions/onboarding-website-intel/index.ts must own a `catch` " +
        "clause. Currently it has only `finally { clearTimeout(...) }` (no catch), " +
        "so fetch errors fall through to the outer handler instead of being answered " +
        "with a fetch-specific fallback.",
    );

    assert(
      analysis!.catchBody !== null,
      "AC#12 RED — the `catch` clause of the fetch `try` block must have a non-empty body.",
    );

    // AC#12 (primary assertion) — the fetch catch MUST return `confidence: 0.35`.
    assertStringIncludes(
      analysis!.catchBody!,
      "confidence: 0.35",
      "AC#12 RED — the `catch` clause of the fetch `try` block must return " +
        "`confidence: 0.35` (not `0`). The current `catch` body does not include " +
        "`0.35`.",
    );

    // AC#12 (defensive assertion) — the fetch catch MUST NOT return `confidence: 0`.
    // Use a negative lookbehind to avoid matching cnpj_confidence /
    // telefone_confidence / vertical_confidence sub-fields (which may legitimately
    // stay 0 — the AC only governs the top-level `confidence` value).
    const zeroConfidenceRe = /(?<![a-zA-Z_])confidence\s*:\s*0(?!\d|\.)/;
    assertEquals(
      zeroConfidenceRe.test(analysis!.catchBody!),
      false,
      "AC#12 RED — the `catch` clause of the fetch `try` block must not return " +
        "top-level `confidence: 0`. The fetch error path must answer with " +
        "`confidence: 0.35` only.",
    );
  },
});
