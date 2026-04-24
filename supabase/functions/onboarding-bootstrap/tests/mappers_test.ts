// Deno tests for the edge-function mappers port.
//
// Run with:
//   deno test --allow-none supabase/functions/onboarding-bootstrap/tests/mappers_test.ts
//
// Parity with apps/landing/src/onboarding/mappers.ts is enforced by the
// landing vitest suite (apps/landing/src/onboarding/mappers.test.ts);
// the cases below guard the Deno port on its own so CI catches drift
// independently of the TS build.

import { assert, assertEquals } from "https://deno.land/std@0.224.0/assert/mod.ts";
import {
  mapBusinessDNAToCompanyProfile,
  mapContactToTeamStructure,
  mapRulesToPolicies,
  mapStateToCurrentMoment,
  type OnboardingState,
} from "../mappers.ts";

const BASE: OnboardingState = {
  authMethod: "email",
  nome: "Fulana",
  email: "fulana@acme.com",
  empresa: "Acme LTDA",
  vertical: "ecommerce",
  porte: "pequena",
  website: "acme.com",
  dataPath: "systems",
  systems: ["shopify", "bigquery"],
  csvUploaded: false,
  googleDriveConnected: false,
  agents: ["analytics", "crm"],
  approvalTasks: ["make_payment"],
  routines: ["daily_sales_digest"],
  notifyChannel: "email",
};

Deno.test("mapBusinessDNAToCompanyProfile maps happy path", () => {
  const out = mapBusinessDNAToCompanyProfile(BASE);
  assertEquals(out.legal_name, "Acme LTDA");
  assertEquals(out.trading_name, "Acme LTDA");
  assertEquals(out.industry, "E-commerce / Varejo");
  assertEquals(out.employee_count_range, "11-50");
  assertEquals(out.tagline, "acme.com");
  assertEquals(out.core_values, []);
});

Deno.test("mapBusinessDNAToCompanyProfile omits absent fields", () => {
  const out = mapBusinessDNAToCompanyProfile({
    ...BASE,
    empresa: "   ",
    vertical: null,
    porte: "",
    website: "",
  });
  assertEquals(out.legal_name, undefined);
  assertEquals(out.industry, undefined);
  assertEquals(out.employee_count_range, undefined);
  assertEquals(out.tagline, undefined);
});

Deno.test("mapContactToTeamStructure builds key_contacts when nome set", () => {
  const out = mapContactToTeamStructure(BASE);
  assertEquals(out.main_contact, "Fulana");
  assertEquals(out.key_contacts?.length, 1);
  assertEquals(out.communication_channels, { email: "fulana@acme.com" });
});

Deno.test("mapContactToTeamStructure handles whatsapp channel", () => {
  const out = mapContactToTeamStructure({ ...BASE, notifyChannel: "whatsapp" });
  assertEquals(out.communication_channels, {
    email: "fulana@acme.com",
    whatsapp: "pendente",
  });
});

Deno.test("mapRulesToPolicies partitions approval vs autonomous", () => {
  const out = mapRulesToPolicies(BASE);
  const appr = out.approval_requirements!;
  // Partition is complete across all 8 tasks.
  assertEquals(appr.requires_approval.length + appr.autonomous.length, 8);
  assert(appr.requires_approval.includes("Realizar pagamentos"));
  assert(!appr.autonomous.includes("Realizar pagamentos"));
});

Deno.test("mapStateToCurrentMoment records systems + agents priorities", () => {
  const out = mapStateToCurrentMoment(BASE);
  const priorities = out.current_priorities ?? [];
  assert(
    priorities.some((p) =>
      p.includes("Integrar sistemas operacionais: shopify, bigquery")
    ),
  );
  assert(priorities.some((p) => p.includes("Ativar agentes: analytics, crm")));
  assert(typeof out.last_updated === "string");
});

Deno.test("mapStateToCurrentMoment emits files/scratch labels", () => {
  const filesOut = mapStateToCurrentMoment({
    ...BASE,
    dataPath: "files",
    systems: [],
    agents: [],
  });
  assert(
    filesOut.current_priorities!.includes(
      "Operar a partir de planilhas e documentos",
    ),
  );
  const scratchOut = mapStateToCurrentMoment({
    ...BASE,
    dataPath: "scratch",
    systems: [],
    agents: [],
  });
  assert(
    scratchOut.current_priorities!.includes(
      "Começar a estruturar dados do zero",
    ),
  );
});
