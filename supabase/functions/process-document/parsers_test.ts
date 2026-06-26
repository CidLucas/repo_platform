// supabase/functions/process-document/parsers_test.ts
//
// B-4 AC-4: parsers XLSX/PPTX devem extrair conteúdo de planilhas multi-sheet
// e apresentações multi-slide.
//
// RED test (TDD-style): as funcoes parseXlsx e parsePptx NAO estao exportadas
// de index.ts — o import abaixo falhara com "does not provide an export named".
// Isso e TRUE RED. O coder deve exporta-las (ou mover para parsers.ts) para
// que o teste compile e passe.
//
// Comportamento esperado (AC-4):
//   1. parseXlsx recebe 3-sheet workbook e devolve texto contendo os 3 sheet names
//      + dados unicos de cada sheet.
//   2. parsePptx recebe 5-slide PPTX e devolve texto contendo os 5 slide titles
//      + bodies unicos de cada slide.
//
// Run:
//   deno test --allow-read --allow-net --allow-env --no-check \
//     --config supabase/functions/deno.json \
//     supabase/functions/process-document/parsers_test.ts --filter B-4

import { assert, assertEquals } from "https://deno.land/std@0.224.0/assert/mod.ts";
import XLSX from "npm:xlsx@0.18.5";
import JSZip from "npm:jszip@3.10.1";
// RED: parseXlsx e parsePptx NAO estao exportadas de index.ts
// O coder deve exporta-las para o teste compilar.
import { parsePptx, parseXlsx } from "./index.ts";

// Stub env vars que index.ts exige no top-level
Deno.env.set("SUPABASE_URL", "http://localhost");
Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", "test-key");
Deno.env.set("SUPABASE_DB_URL", "postgres://localhost/test");

const SHEET_NAMES = ["Receitas", "Despesas", "FluxoCaixa"] as const;
// Unique marker per sheet — if the parser drops a sheet, this test fails.
const SHEET_MARKERS = ["ALPHA-MARKER-001", "BETA-MARKER-002", "GAMMA-MARKER-003"] as const;
const SLIDE_TITLES = [
  "Q1 Visão Geral",
  "Q2 Resultados",
  "Q3 Projeções",
  "Q4 Riscos",
  "Conclusão Executiva",
] as const;
// Unique body per slide — if the parser drops a slide, this test fails.
const SLIDE_BODIES = [
  "BODY-UNIQUE-SLIDE-1",
  "BODY-UNIQUE-SLIDE-2",
  "BODY-UNIQUE-SLIDE-3",
  "BODY-UNIQUE-SLIDE-4",
  "BODY-UNIQUE-SLIDE-5",
] as const;

function buildXlsxBytes(): Uint8Array {
  const wb = XLSX.utils.book_new();
  SHEET_NAMES.forEach((name, idx) => {
    const ws = XLSX.utils.aoa_to_sheet([
      ["coluna_a", "coluna_b"],
      [SHEET_MARKERS[idx], 100 * (idx + 1)],
      [3, 4],
    ]);
    XLSX.utils.book_append_sheet(wb, ws, name);
  });
  const out = XLSX.write(wb, { type: "array", bookType: "xlsx" });
  return new Uint8Array(out as ArrayBuffer);
}

function buildSlideXml(title: string, body: string): string {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr/>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="2" name="Title"/>
          <p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
          <p:nvPr><p:ph type="title"/></p:nvPr>
        </p:nvSpPr>
        <p:spPr/>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:r>
              <a:rPr lang="pt-BR" dirty="0"/>
              <a:t>${title}</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="3" name="Body"/>
          <p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
          <p:nvPr><p:ph idx="1"/></p:nvPr>
        </p:nvSpPr>
        <p:spPr/>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:r>
              <a:rPr lang="pt-BR" dirty="0"/>
              <a:t>${body}</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>`;
}

async function buildPptxBytes(): Promise<Uint8Array> {
  const zip = new JSZip();
  // Minimal Content_Types.xml so Office recognises the .pptx
  zip.file(
    "[Content_Types].xml",
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
  <Override PartName="/ppt/slides/slide2.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
  <Override PartName="/ppt/slides/slide3.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
  <Override PartName="/ppt/slides/slide4.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
  <Override PartName="/ppt/slides/slide5.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>`,
  );
  zip.file(
    "ppt/presentation.xml",
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>`,
  );
  SLIDE_TITLES.forEach((title, idx) => {
    const n = idx + 1;
    zip.file(
      `ppt/slides/slide${n}.xml`,
      buildSlideXml(title, SLIDE_BODIES[idx]),
    );
  });
  return new Uint8Array(await zip.generateAsync({ type: "arraybuffer" }));
}

Deno.test({
  name: "B-4 AC-4 — parseXlsx extrai todas as 3 sheets do workbook",
  fn: async () => {
    const bytes = buildXlsxBytes();
    const text = await parseXlsx(bytes);
    for (const name of SHEET_NAMES) {
      assert(
        text.includes(name),
        `parseXlsx output missing sheet name "${name}". Got: ${text.slice(0, 200)}`,
      );
    }
  },
});

Deno.test({
  name: "B-4 AC-4 — parsePptx extrai os 5 slide titles",
  fn: async () => {
    const bytes = await buildPptxBytes();
    const text = await parsePptx(bytes);
    for (const title of SLIDE_TITLES) {
      assert(
        text.includes(title),
        `parsePptx output missing slide title "${title}". Got: ${text.slice(0, 200)}`,
      );
    }
  },
});

Deno.test({
  name: "B-4 AC-4 — parseXlsx preserva contagem e ordem das 3 sheets",
  fn: async () => {
    const bytes = buildXlsxBytes();
    const text = await parseXlsx(bytes);
    const positions = SHEET_NAMES.map((n) => text.indexOf(n));
    for (const pos of positions) {
      assert(pos >= 0, `Sheet name not found at any position: ${positions}`);
    }
    assert(
      positions[0] < positions[1] && positions[1] < positions[2],
      `Sheets out of order. Positions: ${JSON.stringify(positions)}`,
    );
  },
});

Deno.test({
  name: "B-4 AC-4 — parsePptx preserva contagem e ordem dos 5 slides",
  fn: async () => {
    const bytes = await buildPptxBytes();
    const text = await parsePptx(bytes);
    const positions = SLIDE_TITLES.map((t) => text.indexOf(t));
    for (const pos of positions) {
      assert(pos >= 0, `Slide title not found at any position: ${positions}`);
    }
    for (let i = 1; i < positions.length; i++) {
      assert(
        positions[i - 1] < positions[i],
        `Slides out of order at index ${i}. Positions: ${JSON.stringify(positions)}`,
      );
    }
  },
});

Deno.test({
  name: "B-4 AC-4 — parseXlsx emite EXATAMENTE 3 sheet headers",
  fn: async () => {
    const bytes = buildXlsxBytes();
    const text = await parseXlsx(bytes);
    const headerMatches = text.match(/^## /gm) ?? [];
    assertEquals(
      headerMatches.length,
      SHEET_NAMES.length,
      `Expected ${SHEET_NAMES.length} sheet headers ("## "), got ${headerMatches.length}. Output: ${text}`,
    );
  },
});

Deno.test({
  name: "B-4 AC-4 — parseXlsx preserva dados únicos de CADA sheet (catches dropped-sheet bug)",
  fn: async () => {
    const bytes = buildXlsxBytes();
    const text = await parseXlsx(bytes);
    for (let i = 0; i < SHEET_NAMES.length; i++) {
      const marker = SHEET_MARKERS[i];
      assert(
        text.includes(marker),
        `parseXlsx output missing data from sheet "${SHEET_NAMES[i]}" (marker "${marker}"). ` +
          `This catches the "only first sheet processed" regression. Output:\n${text}`,
      );
    }
  },
});

Deno.test({
  name: "B-4 AC-4 — parsePptx preserva body único de CADA slide (catches dropped-slide bug)",
  fn: async () => {
    const bytes = await buildPptxBytes();
    const text = await parsePptx(bytes);
    for (let i = 0; i < SLIDE_TITLES.length; i++) {
      const body = SLIDE_BODIES[i];
      assert(
        text.includes(body),
        `parsePptx output missing body from slide "${SLIDE_TITLES[i]}" (marker "${body}"). ` +
          `This catches the "only first slide processed" regression. Output:\n${text}`,
      );
    }
  },
});
