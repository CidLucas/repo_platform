import { beforeEach, describe, expect, it, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mock the Supabase client so no network calls happen and we can assert the
// exact PostgREST/RPC/Edge-fn shape the service emits.
//
// vi.mock is hoisted, so anything it touches must come from vi.hoisted().
// ---------------------------------------------------------------------------

type SessionShape = {
  user: { id: string; email: string };
  provider_refresh_token?: string | null;
  provider_token?: string | null;
};

const mocks = vi.hoisted(() => {
  const state: {
    session: SessionShape | null;
    user: { id: string; email: string } | null;
    lastUpdate?: { payload: Record<string, unknown>; filter?: [string, string] };
    lastMaybeSingle?: unknown;
  } = {
    session: null,
    user: null,
  };
  return {
    state,
    rpc: vi.fn(async () => ({ data: null, error: null })) as unknown as ReturnType<
      typeof vi.fn
    >,
    invoke: vi.fn(async () => ({
      data: { connected: true, account_email: "u@acme.com" },
      error: null,
    })) as unknown as ReturnType<typeof vi.fn>,
  };
});

vi.mock("../../lib/supabase", () => {
  function makeTableBuilder() {
    const builder: Record<string, unknown> = {};
    builder.select = vi.fn(() => builder);
    builder.update = vi.fn((payload: Record<string, unknown>) => {
      mocks.state.lastUpdate = { payload };
      return builder;
    });
    builder.eq = vi.fn((col: string, val: string) => {
      if (mocks.state.lastUpdate) mocks.state.lastUpdate.filter = [col, val];
      return builder;
    });
    builder.maybeSingle = vi.fn(async () => ({
      data: mocks.state.lastMaybeSingle ?? null,
      error: null,
    }));
    (builder as { then?: unknown }).then = (resolve: (v: unknown) => unknown) =>
      resolve({ data: null, error: null });
    return builder;
  }
  return {
    supabase: {
      auth: {
        getSession: async () => ({
          data: { session: mocks.state.session },
          error: null,
        }),
        getUser: async () => ({ data: { user: mocks.state.user }, error: null }),
      },
      from: vi.fn(() => makeTableBuilder()),
      rpc: mocks.rpc,
      functions: { invoke: mocks.invoke },
    },
  };
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

import {
  captureDriveToken,
  ensureTenantRow,
  getOnboardingState,
  patchOnboardingState,
  runBootstrap,
  saveContextSections,
  updateClientColumn,
} from "./onboardingService";

const { state, rpc, invoke } = mocks;

beforeEach(() => {
  rpc.mockClear();
  invoke.mockClear();
  state.session = {
    user: { id: "user-1", email: "u@acme.com" },
    provider_refresh_token: "refresh-xyz",
    provider_token: "access-abc",
  };
  state.user = { id: "user-1", email: "u@acme.com" };
  state.lastUpdate = undefined;
  state.lastMaybeSingle = undefined;
});

describe("getOnboardingState", () => {
  it("returns null when no session", async () => {
    state.session = null;
    await expect(getOnboardingState()).resolves.toBeNull();
  });

  it("returns the row payload when present", async () => {
    state.lastMaybeSingle = {
      onboarding_state: { empresa: "Acme" },
      onboarding_completed_at: null,
    };
    const out = await getOnboardingState();
    expect(out).toEqual({
      onboarding_state: { empresa: "Acme" },
      onboarding_completed_at: null,
    });
  });

  it("coerces missing keys to empty object / null", async () => {
    state.lastMaybeSingle = {};
    const out = await getOnboardingState();
    expect(out).toEqual({ onboarding_state: {}, onboarding_completed_at: null });
  });
});

describe("patchOnboardingState", () => {
  it("no-ops on empty patch", async () => {
    await patchOnboardingState({});
    expect(rpc).not.toHaveBeenCalled();
  });

  it("no-ops when not authenticated", async () => {
    state.session = null;
    await patchOnboardingState({ empresa: "Acme" });
    expect(rpc).not.toHaveBeenCalled();
  });

  it("calls merge_onboarding_state RPC with the patch", async () => {
    await patchOnboardingState({ empresa: "Acme", vertical: "ecommerce" });
    expect(rpc).toHaveBeenCalledWith("merge_onboarding_state", {
      p_patch: { empresa: "Acme", vertical: "ecommerce" },
    });
  });

  it("throws when the RPC surfaces an error", async () => {
    rpc.mockResolvedValueOnce({ data: null, error: { message: "boom" } });
    await expect(
      patchOnboardingState({ empresa: "Acme" }),
    ).rejects.toBeTruthy();
  });
});

describe("saveContextSections", () => {
  it("no-ops when no fields are provided", async () => {
    await saveContextSections({});
    expect(state.lastUpdate).toBeUndefined();
  });

  it("only writes provided keys", async () => {
    await saveContextSections({
      company_profile: { legal_name: "Acme", core_values: [] },
    });
    expect(state.lastUpdate?.payload).toEqual({
      company_profile: { legal_name: "Acme", core_values: [] },
    });
    expect(state.lastUpdate?.filter).toEqual(["external_user_id", "user-1"]);
  });
});

describe("updateClientColumn", () => {
  it("writes the scalar column scoped by external_user_id", async () => {
    await updateClientColumn("nome_empresa", "Acme");
    expect(state.lastUpdate?.payload).toEqual({ nome_empresa: "Acme" });
    expect(state.lastUpdate?.filter).toEqual(["external_user_id", "user-1"]);
  });
});

describe("runBootstrap", () => {
  it("invokes the onboarding-bootstrap edge function with the full payload", async () => {
    invoke.mockResolvedValueOnce({
      data: { client_id: "c1", agents: 2, routines: 1, prompts_seeded: 2 },
      error: null,
    });
    const payload = {
      authMethod: "email",
      nome: "",
      email: "",
      empresa: "",
      vertical: null,
      porte: "",
      website: "",
      dataPath: null,
      systems: [],
      csvUploaded: false,
      googleDriveConnected: false,
      agents: [],
      approvalTasks: [],
      routines: [],
      notifyChannel: "email",
    } as Parameters<typeof runBootstrap>[0];

    const out = await runBootstrap(payload);
    expect(invoke).toHaveBeenCalledWith("onboarding-bootstrap", {
      body: payload,
    });
    expect(out.client_id).toBe("c1");
  });

  it("throws when the edge function errors", async () => {
    invoke.mockResolvedValueOnce({ data: null, error: { message: "nope" } });
    await expect(runBootstrap({} as never)).rejects.toBeTruthy();
  });
});

describe("captureDriveToken", () => {
  it("returns connected=false when no session", async () => {
    state.session = null;
    const out = await captureDriveToken();
    expect(out).toEqual({ connected: false });
    expect(invoke).not.toHaveBeenCalled();
  });

  it("returns connected=false when Google omits the refresh token", async () => {
    state.session = {
      user: { id: "user-1", email: "u@acme.com" },
      provider_refresh_token: null,
      provider_token: "access-abc",
    };
    const out = await captureDriveToken();
    expect(out).toEqual({ connected: false });
    expect(invoke).not.toHaveBeenCalled();
  });

  it("forwards refresh + access tokens to the edge function", async () => {
    await captureDriveToken();
    expect(invoke).toHaveBeenCalledWith("onboarding-capture-drive-token", {
      body: {
        provider_refresh_token: "refresh-xyz",
        provider_token: "access-abc",
        account_email: "u@acme.com",
      },
    });
  });

  it("returns connected=false when the edge fn errors", async () => {
    invoke.mockResolvedValueOnce({ data: null, error: { message: "x" } });
    const out = await captureDriveToken();
    expect(out).toEqual({ connected: false });
  });
});

describe("ensureTenantRow", () => {
  it("no-ops without a session", async () => {
    state.session = null;
    await ensureTenantRow();
    expect(rpc).not.toHaveBeenCalled();
  });

  it("calls ensure_tenant_row when authenticated", async () => {
    await ensureTenantRow();
    expect(rpc).toHaveBeenCalledWith("ensure_tenant_row");
  });
});
