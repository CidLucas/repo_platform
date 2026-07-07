# Fix: Onboarding StepData crash + CORS on edge function

## Bug 1: `showSchemaTypeRadios is not defined` — ReferenceError crash

**File:** apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx

**Root cause:** The `StepData` component (starting at line 1116) uses `showSchemaTypeRadios` in the JSX (lines 1394, 1424) and calls `setShowSchemaTypeRadios` (lines 1420, 1425), but the corresponding `useState` declaration is **missing** from the state declarations block (lines 1128-1143).

**Fix:** Add the missing state after line 1135 (after `setShowClassificationModal`):
```ts
const [showSchemaTypeRadios, setShowSchemaTypeRadios] = useState(true)
```

Default `true` so the radio buttons are visible when the classification modal first opens.

## Bug 2: CORS preflight fails on `onboarding-cnpj-enrich`

**File:** supabase/functions/onboarding-cnpj-enrich/index.ts

**Root cause:** The function was deployed but its CORS OPTIONS handler isn't working. The `Deno.serve` handler does handle OPTIONS (lines 126-128), but the `handleCnpjEnrich` function (lines 91-121) catches ALL errors silently and returns via `json()` which does include CORS headers. However, the error at the browser says "Response to preflight request doesn't pass access control check: It does not have HTTP ok status" — this typically means the Supabase gateway itself returns a non-200 before the function code runs.

**Fix:** Verify the function is deployed with the latest code. If it was deployed before the CORS handler was added, it needs redeploying. The correct command would be:
```
npx supabase functions deploy onboarding-cnpj-enrich
```

But we should also check if there's a `supabase/config.toml` with `verify_jwt = true` that might be blocking unauthenticated OPTIONS requests.

## Bug 3: Single file upload limitation

**File:** apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx

**Current behavior:** The hidden `<input>` at line 1461-1467 doesn't have `multiple` attribute, and `handleCsvChange` at line 1249-1259 only processes `e.target.files[0]`.

**Fix:** The user wants to upload a single spreadsheet file per flow (the classification modal handles one file at a time). The current single-file behavior is intentional for the onboarding flow. No change needed unless the user requests multi-file support.

## Instructions

Please fix Bug 1 (the missing `useState` declaration). For Bug 2, verify the function code and report if the CORS headers look correct. For Bug 3, the single-file upload is by design — no changes needed.
