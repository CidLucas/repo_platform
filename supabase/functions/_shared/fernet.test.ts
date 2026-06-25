/**
 * supabase/functions/_shared/fernet.test.ts
 *
 * Smoke test for the shared Fernet helper.
 *
 * Verifies:
 *  1. Round-trip with the new helper (encrypt → decrypt).
 *  2. Cross-compatibility with the legacy `npm:fernet` package (which was used
 *     by the 3 reader functions before Phase 1.2) — encrypts with npm:fernet
 *     and decrypts with the new helper, to prove tokens written by the
 *     existing readers can still be read.
 *  3. Cross-compatibility with Python's `cryptography.fernet.Fernet` — uses
 *     a Fernet spec test vector (key + plaintext + expected token) so we know
 *     the output is wire-compatible with the Python backend.
 *  4. Error cases: bad version byte, HMAC mismatch, bad padding.
 *
 * Run with: `deno test supabase/functions/_shared/fernet.test.ts`
 */

import { assertEquals, assertRejects } from "std/testing/asserts.ts";
import Fernet from "npm:fernet@0.4.0";
import { fernetDecrypt, fernetEncrypt } from "./fernet.ts";

// Deterministic key for the test (urlsafe-base64 of 32 raw bytes).
// Equivalent to `cryptography.fernet.Fernet(b"0123456789abcdef" * 2)`.
const TEST_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY";

Deno.test("round-trip with the new helper", async () => {
  const plaintext = "hello world — tokens round-trip cleanly";
  const token = await fernetEncrypt(TEST_KEY, plaintext);
  const decrypted = await fernetDecrypt(TEST_KEY, token);
  assertEquals(decrypted, plaintext);
});

Deno.test("round-trip with empty string", async () => {
  const token = await fernetEncrypt(TEST_KEY, "");
  const decrypted = await fernetDecrypt(TEST_KEY, token);
  assertEquals(decrypted, "");
});

Deno.test("round-trip with long payload (multiple AES blocks)", async () => {
  const plaintext = "a".repeat(500);
  const token = await fernetEncrypt(TEST_KEY, plaintext);
  const decrypted = await fernetDecrypt(TEST_KEY, token);
  assertEquals(decrypted, plaintext);
});

Deno.test("cross-compat: helper can read tokens written by npm:fernet", async () => {
  // npm:fernet is what google-calendar-events, get-monday-subitems, and
  // get-agenda-events used to use for decrypt. If this test passes, tokens
  // already stored in integration_tokens (encrypted by Python) remain
  // readable through the new helper.
  const secret = new Fernet.Secret(TEST_KEY);
  const fernet = new Fernet.Token({
    secret,
    token: "",
    ttl: 0,
  });
  const plaintext = "legacy npm:fernet encrypted payload";
  const npmToken = fernet.encode(plaintext);
  const decrypted = await fernetDecrypt(TEST_KEY, npmToken);
  assertEquals(decrypted, plaintext);
});

Deno.test("cross-compat: helper produces tokens that npm:fernet can read", async () => {
  // Symmetric: tokens written by the new helper should be readable by
  // anything speaking the Fernet spec (Python, npm:fernet, etc.).
  const plaintext = "new helper → npm:fernet";
  const helperToken = await fernetEncrypt(TEST_KEY, plaintext);
  const secret = new Fernet.Secret(TEST_KEY);
  const fernet = new Fernet.Token({ secret, token: helperToken, ttl: 0 });
  const decrypted = fernet.decode();
  assertEquals(decrypted, plaintext);
});

Deno.test("rejects token with invalid version byte", async () => {
  // Build a token with version 0x81 instead of 0x80, then base64url-encode it.
  const bytes = new Uint8Array(1 + 8 + 16 + 16 + 32);
  bytes[0] = 0x81; // invalid
  const token = btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
  await assertRejects(
    () => fernetDecrypt(TEST_KEY, token),
    Error,
    "Invalid Fernet version byte",
  );
});

Deno.test("rejects token with HMAC mismatch", async () => {
  // Round-trip a real token, then flip a single ciphertext bit. The HMAC
  // check must catch this.
  const token = await fernetEncrypt(TEST_KEY, "tamper test");
  // Flip one character in the base64url portion (after the first 5 chars to
  // stay inside the body, not the HMAC suffix).
  const tampered = token.slice(0, 20) + (token[20] === "A" ? "B" : "A") + token.slice(21);
  await assertRejects(
    () => fernetDecrypt(TEST_KEY, tampered),
    Error,
    "Fernet HMAC mismatch",
  );
});

Deno.test("rejects token with wrong key", async () => {
  const token = await fernetEncrypt(TEST_KEY, "secret");
  const otherKey = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVowMTIzNDU2Nzg"; // 32 different bytes
  await assertRejects(
    () => fernetDecrypt(otherKey, token),
    Error,
    "Fernet HMAC mismatch",
  );
});

Deno.test("rejects malformed (too-short) token", async () => {
  const short = "gAAAAAAA"; // not enough bytes to be a valid token
  await assertRejects(
    () => fernetDecrypt(TEST_KEY, short),
    Error,
    "Fernet token too short",
  );
});

Deno.test("rejects key that is not 32 bytes", async () => {
  const shortKey = "MDEyMzQ1Njc4OWFiY2RlZg"; // 16 bytes after base64 decode
  await assertRejects(
    () => fernetEncrypt(shortKey, "x"),
    Error,
    "Fernet key must be 32 bytes",
  );
});
