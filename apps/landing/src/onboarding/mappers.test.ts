import { describe, expect, it } from "vitest";

import {
  mapBusinessDNAToCompanyProfile,
  mapContactToTeamStructure,
  mapRulesToPolicies,
} from "./mappers";
import type { OnboardingState } from "./state";

const BASE: OnboardingState = {
  persona: null,
  painPoint: null,
  teamSize: null,
  firstApprovalDecision: null,
  authMethod: "email",
  nome: "Fulana de Tal",
  email: "fulana@acme.com",
  empresa: "Acme LTDA",
  vertical: "ecommerce",
  porte: "pequena",
  website: "acme.com",
  primaryFocus: "vendas",
  dataPath: "systems",
  systems: ["shopify", "bigquery"],
  csvUploaded: false,
  googleDriveConnected: false,
  columnMapping: [],
  agents: ["analytics", "crm"],
  approvalTasks: ["make_payment", "supplier_order"],
  alwaysRequireApproval: true,
  routines: ["daily_sales_digest"],
  notifyChannel: "email",
  kpiSelections: {},
};

// Every vertical enum value must map to a non-empty industry label. Keeps
// the mapper in sync with the Vertical union in state.ts.
const ALL_VERTICALS: Exclude<OnboardingState["vertical"], null>[] = [
  "ecommerce",
  "servicos",
  "industria",
  "saude",
  "educacao",
  "financeiro",
  "agro",
  "outro",
];

describe("mapBusinessDNAToCompanyProfile", () => {
  it("maps empresa, vertical, porte, website", () => {
    const out = mapBusinessDNAToCompanyProfile(BASE);
    expect(out.legal_name).toBe("Acme LTDA");
    expect(out.trading_name).toBe("Acme LTDA");
    expect(out.industry).toBe("E-commerce / Varejo");
    expect(out.employee_count_range).toBe("11-50");
    expect(out.tagline).toBe("acme.com");
    expect(out.core_values).toEqual([]);
  });

  it("omits absent fields — never invents data", () => {
    const out = mapBusinessDNAToCompanyProfile({
      ...BASE,
      empresa: "   ",
      vertical: null,
      porte: "",
      website: "",
    });
    expect(out.legal_name).toBeUndefined();
    expect(out.industry).toBeUndefined();
    expect(out.employee_count_range).toBeUndefined();
    expect(out.tagline).toBeUndefined();
    // core_values must always be present (seed).
    expect(out.core_values).toEqual([]);
  });

  it("covers every vertical enum value", () => {
    for (const v of ALL_VERTICALS) {
      const out = mapBusinessDNAToCompanyProfile({ ...BASE, vertical: v });
      expect(out.industry).toBeTruthy();
      expect(typeof out.industry).toBe("string");
    }
  });

  it("maps every known porte bucket to a range string", () => {
    for (const porte of ["solo", "micro", "pequena", "media", "grande"]) {
      const out = mapBusinessDNAToCompanyProfile({ ...BASE, porte });
      expect(out.employee_count_range).toBeTruthy();
    }
  });

  it("ignores unknown porte values instead of emitting garbage", () => {
    const out = mapBusinessDNAToCompanyProfile({
      ...BASE,
      porte: "gigante-intergalactica",
    });
    expect(out.employee_count_range).toBeUndefined();
  });
});

describe("mapContactToTeamStructure", () => {
  it("builds key_contacts when nome is set", () => {
    const out = mapContactToTeamStructure(BASE);
    expect(out.main_contact).toBe("Fulana de Tal");
    expect(out.key_contacts).toEqual([
      {
        role: "Fundador / Operação",
        name: "Fulana de Tal",
        contact_preference: "email",
      },
    ]);
    expect(out.communication_channels).toEqual({ email: "fulana@acme.com" });
    expect(out.escalation_path).toEqual([]);
    expect(out.operational_locations).toEqual([]);
  });

  it("leaves key_contacts empty when nome missing", () => {
    const out = mapContactToTeamStructure({ ...BASE, nome: "" });
    expect(out.key_contacts).toEqual([]);
    expect(out.main_contact).toBeUndefined();
  });

  it.each([
    ["whatsapp", { email: "fulana@acme.com", whatsapp: "pendente" }],
    ["app", { email: "fulana@acme.com", app: "dashboard" }],
    ["email", { email: "fulana@acme.com" }],
  ] as const)(
    "produces the right communication_channels for notifyChannel=%s",
    (notifyChannel, expected) => {
      const out = mapContactToTeamStructure({ ...BASE, notifyChannel });
      expect(out.communication_channels).toEqual(expected);
    },
  );

  it("drops email entry when user email is empty", () => {
    const out = mapContactToTeamStructure({ ...BASE, email: "" });
    expect(out.communication_channels).toEqual({});
  });
});

describe("mapRulesToPolicies", () => {
  it("splits approval tasks into requires_approval vs autonomous", () => {
    const out = mapRulesToPolicies(BASE);
    const appr = out.approval_requirements!;
    expect(appr.requires_approval).toEqual(
      expect.arrayContaining(["Realizar pagamentos", "Fazer pedidos a fornecedores"]),
    );
    // Tasks NOT selected by the user land in autonomous.
    expect(appr.autonomous).toEqual(
      expect.arrayContaining([
        "Enviar e-mails",
        "Enviar mensagens",
        "Marcar compromissos",
        "Publicar em redes sociais",
        "Alterar preços e catálogo",
        "Compartilhar relatórios",
      ]),
    );
    // Partition is complete: 8 total, 2 approval + 6 autonomous.
    expect(appr.requires_approval.length + appr.autonomous.length).toBe(8);
  });

  it("leaves requires_approval empty when no tasks are selected", () => {
    const out = mapRulesToPolicies({ ...BASE, approvalTasks: [] });
    expect(out.approval_requirements!.requires_approval).toEqual([]);
    expect(out.approval_requirements!.autonomous.length).toBe(8);
  });
});

