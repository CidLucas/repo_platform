import { assert, assertEquals, assertFalse, assertStrictEquals } from "jsr:@std/assert";
import {
  calculateConfidence,
  detectVertical,
  extractCNPJ,
  extractPhone,
  validateCNPJ,
} from "./index.ts";

Deno.test("extractCNPJ returns formatted CNPJ from HTML body", () => {
  const html = `
    <html>
      <body>
        <p>Empresa Teste LTDA - CNPJ 11.444.777/0001-61</p>
        <p>Inscrição estadual: 123.456.789.012</p>
      </body>
    </html>
  `;
  const result = extractCNPJ(html);
  assertEquals(result, "11.444.777/0001-61");
});

Deno.test("extractCNPJ finds CNPJ in meta tags (og:*, article:*, business:*)", () => {
  const html = `
    <html>
      <head>
        <meta property="og:CNPJ" content="11.444.777/0001-61" />
        <meta property="article:author" content="Empresa X" />
        <meta property="business:contact_data" content="11.444.777/0001-61" />
      </head>
      <body>nothing here</body>
    </html>
  `;
  const result = extractCNPJ(html);
  assertEquals(result, "11.444.777/0001-61");
});

Deno.test("extractCNPJ finds CNPJ inside JSON-LD script tag", () => {
  const html = `
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "Empresa Y",
          "taxID": "11.444.777/0001-61"
        }
        </script>
      </head>
      <body>content</body>
    </html>
  `;
  const result = extractCNPJ(html);
  assertEquals(result, "11.444.777/0001-61");
});

Deno.test("extractCNPJ returns null when no CNPJ is present", () => {
  const html = `
    <html>
      <body>
        <p>This page has no business registration number at all.</p>
        <p>Just a phone: (11) 1234-5678</p>
      </body>
    </html>
  `;
  const result = extractCNPJ(html);
  assertStrictEquals(result, null);
});

Deno.test("validateCNPJ returns true for valid CNPJ 11.444.777/0001-61", () => {
  const result = validateCNPJ("11.444.777/0001-61");
  assert(result);
});

Deno.test("validateCNPJ returns false for CNPJ with wrong check digits 11.444.777/0001-99", () => {
  const result = validateCNPJ("11.444.777/0001-99");
  assertFalse(result);
});

Deno.test("extractPhone matches (11) 91234-5678", () => {
  const html = `
    <html>
      <body>
        <p>Entre em contato: (11) 91234-5678</p>
        <p>Horário de atendimento: 9h às 18h</p>
      </body>
    </html>
  `;
  const result = extractPhone(html);
  assertEquals(result, "(11) 91234-5678");
});

Deno.test("extractPhone returns null for international format +55 11 91234-5678", () => {
  const html = `
    <html>
      <body>
        <p>Call us at +55 11 91234-5678</p>
      </body>
    </html>
  `;
  const result = extractPhone(html);
  assertStrictEquals(result, null);
});

Deno.test("extractPhone returns null when no phone is present", () => {
  const html = `
    <html>
      <body>
        <p>Send us an email at contact@example.com</p>
      </body>
    </html>
  `;
  const result = extractPhone(html);
  assertStrictEquals(result, null);
});

Deno.test("detectVertical returns the correct vertical for each of 11 categories", () => {
  const cases: Array<{ text: string; expected: string }> = [
    { text: "Loja virtual com checkout e carrinho de compras", expected: "ecommerce" },
    { text: "Distribuidora e atacadista de materiais", expected: "industria" },
    { text: "Clínica médica com hospital e consultório", expected: "saude" },
    { text: "Curso online para alunos da escola", expected: "educacao" },
    { text: "Escritório contábil e financeiro", expected: "financeiro" },
    { text: "Agência de design, logo e branding", expected: "design" },
    { text: "Buffet de eventos para festas e cerimônias", expected: "buffet" },
    { text: "Empresa de construção civil e obras de engenharia", expected: "construcao" },
    { text: "Companhia de logística, frete e transporte com frota", expected: "logistica" },
    { text: "Empresa de assessoria e mentoria para treinamento", expected: "consultoria" },
    { text: "Agência de atendimento e serviços gerais", expected: "servicos" },
  ];

  for (const { text, expected } of cases) {
    const result = detectVertical(text);
    assertEquals(result, expected, `expected detectVertical("${text}") === "${expected}", got ${result}`);
  }
});

Deno.test("calculateConfidence returns 0.0, 0.3, 0.5, 0.7, 0.7 for sourceCount 0, 1, 2, 3, 5", () => {
  assertEquals(calculateConfidence(0), 0.0);
  assertEquals(calculateConfidence(1), 0.3);
  assertEquals(calculateConfidence(2), 0.5);
  assertEquals(calculateConfidence(3), 0.7);
  assertEquals(calculateConfidence(5), 0.7);
});
