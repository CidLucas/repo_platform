import { assertEquals } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { extractCNPJ } from "./index.ts";

Deno.test("extractCNPJ deve extrair CNPJ válido do HTML", () => {
  const html = '<html><body>CNPJ: 12.345.678/0001-90</body></html>';
  const result = extractCNPJ(html);
  assertEquals(result, "12.345.678/0001-90");
});
