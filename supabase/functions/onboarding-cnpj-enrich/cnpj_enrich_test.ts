// supabase/functions/onboarding-cnpj-enrich/cnpj_enrich_test.ts
//
// B-1 AC-1: edge function onboarding-cnpj-enrich deve validar CNPJ
// (14 digitos + digitos verificadores) ANTES de chamar API externa.
//
// RED test (TDD-style): o arquivo supabase/functions/onboarding-cnpj-enrich/index.ts
// NAO existe — o import abaixo de `handleCnpjEnrich` falhara com
// "Module not found" (TS2307) ao carregar o test runner. Isso e TRUE RED.
// O coder deve criar o index.ts exportando `handleCnpjEnrich` para que o
// teste compile e os casos abaixo passem.
//
// Comportamento esperado (AC-1):
//   Para cada CNPJ invalido abaixo, `handleCnpjEnrich` deve retornar
//   uma Response com:
//     - status === 400
//     - body JSON contendo a chave "error" com valor string nao-vazio
//   A edge function NAO deve chamar API externa (Receita Federal,
//   BrasilAPI, etc.) — validacao deve ocorrer localmente.
//
// Run:
//   deno test --allow-read --allow-net --allow-env --no-check \
//     --config supabase/functions/deno.json \
//     supabase/functions/onboarding-cnpj-enrich/cnpj_enrich_test.ts --filter B-1

import {
  assert,
  assertEquals,
} from "https://deno.land/std@0.224.0/assert/mod.ts";
// RED: index.ts NAO existe. O coder deve cria-lo exportando handleCnpjEnrich.
import { handleCnpjEnrich } from "./index.ts";

// CNPJs invalidos para AC-1 (4 casos: curto, repetido, nao-numerico, vazio).
// Estes NAO devem passar pela validacao local de CNPJ.
const INVALID_CNPJS: readonly string[] = [
  "00",                       // muito curto (2 digitos)
  "11111111111111",           // 14 digitos mas todos iguais (rejeitado por sequencia repetida)
  "abcdefghijklmn",           // 14 chars mas nao-numerico
  "",                         // string vazia
];

Deno.test({
  name: "B-1 AC-1 — handleCnpjEnrich retorna status 400 para CNPJ invalido",
  fn: async () => {
    for (const cnpj of INVALID_CNPJS) {
      const req = new Request("https://example.com/onboarding-cnpj-enrich", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cnpj }),
      });

      const res: Response = await handleCnpjEnrich(req);

      assert(
        res instanceof Response,
        `handleCnpjEnrich deve retornar uma Response. Got: ${typeof res}`,
      );
      assertEquals(
        res.status,
        400,
        `CNPJ invalido "${cnpj}" deveria retornar status 400, got ${res.status}`,
      );
    }
  },
});

Deno.test({
  name: "B-1 AC-1 — handleCnpjEnrich retorna body JSON com chave 'error' para CNPJ invalido",
  fn: async () => {
    for (const cnpj of INVALID_CNPJS) {
      const req = new Request("https://example.com/onboarding-cnpj-enrich", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cnpj }),
      });

      const res: Response = await handleCnpjEnrich(req);

      // Body deve ser JSON parseavel.
      const body = await res.json();
      assert(
        body && typeof body === "object" && !Array.isArray(body),
        `Body deve ser um objeto JSON. Got: ${JSON.stringify(body)}`,
      );

      // Chave "error" deve existir e ser string nao-vazia.
      assert(
        "error" in body,
        `Body deve conter chave "error" para CNPJ invalido "${cnpj}". Got keys: ${
          Object.keys(body).join(", ")
        }`,
      );
      assert(
        typeof body.error === "string" && body.error.length > 0,
        `body.error deve ser string nao-vazia. Got: ${JSON.stringify(body.error)} (type: ${typeof body.error})`,
      );
    }
  },
});

Deno.test({
  name: "B-1 AC-1 — handleCnpjEnrich rejeita CNPJ curto '00' com 400 + error",
  fn: async () => {
    const req = new Request("https://example.com/onboarding-cnpj-enrich", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cnpj: "00" }),
    });

    const res = await handleCnpjEnrich(req);

    assertEquals(res.status, 400);
    const body = await res.json();
    assertEquals(typeof body.error, "string");
    assert(body.error.length > 0);
  },
});

Deno.test({
  name: "B-1 AC-1 — handleCnpjEnrich rejeita CNPJ repetido '11111111111111' com 400 + error",
  fn: async () => {
    const req = new Request("https://example.com/onboarding-cnpj-enrich", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cnpj: "11111111111111" }),
    });

    const res = await handleCnpjEnrich(req);

    assertEquals(res.status, 400);
    const body = await res.json();
    assertEquals(typeof body.error, "string");
    assert(body.error.length > 0);
  },
});

Deno.test({
  name: "B-1 AC-1 — handleCnpjEnrich rejeita CNPJ nao-numerico 'abcdefghijklmn' com 400 + error",
  fn: async () => {
    const req = new Request("https://example.com/onboarding-cnpj-enrich", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cnpj: "abcdefghijklmn" }),
    });

    const res = await handleCnpjEnrich(req);

    assertEquals(res.status, 400);
    const body = await res.json();
    assertEquals(typeof body.error, "string");
    assert(body.error.length > 0);
  },
});

Deno.test({
  name: "B-1 AC-1 — handleCnpjEnrich rejeita CNPJ vazio '' com 400 + error",
  fn: async () => {
    const req = new Request("https://example.com/onboarding-cnpj-enrich", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cnpj: "" }),
    });

    const res = await handleCnpjEnrich(req);

    assertEquals(res.status, 400);
    const body = await res.json();
    assertEquals(typeof body.error, "string");
    assert(body.error.length > 0);
  },
});
