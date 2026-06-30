/**
 * supabase/functions/_shared/google_drive.ts
 *
 * Shared helpers for Google Drive access in Edge Functions.
 *
 * - fernetDecrypt: reverse of the encryption in onboarding-capture-drive-token
 * - getAccessToken: load + decrypt + refresh Google token from integration_tokens
 * - driveMetadata: GET /drive/v3/files/{fileId} metadata
 * - driveExportOrDownload: stream file content (export Sheets → XLSX, direct download otherwise)
 */

import { SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2";

// ── Fernet decrypt ───────────────────────────────────────────────────────────
// Mirrors the encrypt in onboarding-capture-drive-token.
// Format: base64url( 0x80 | timestamp(8B BE) | iv(16B) | ciphertext | hmac(32B) )
// Key: URL-safe base64 of 32 bytes: first 16 = signing key, last 16 = AES key.

function base64urlDecode(str: string): Uint8Array {
  const base64 = str.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64 + "==".slice(0, (4 - (base64.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function fernetDecrypt(keyBase64url: string, token: string): Promise<string> {
  const keyBytes = base64urlDecode(keyBase64url);
  if (keyBytes.length !== 32) throw new Error(`Fernet key must be 32 bytes, got ${keyBytes.length}`);

  const signingKey = keyBytes.slice(0, 16);
  const encryptionKey = keyBytes.slice(16, 32);

  const raw = base64urlDecode(token);
  // Layout: version(1) + timestamp(8) + iv(16) + ciphertext(variable) + hmac(32)
  if (raw.length < 1 + 8 + 16 + 32) throw new Error("Fernet token too short");
  if (raw[0] !== 0x80) throw new Error(`Unsupported Fernet version: 0x${raw[0].toString(16)}`);

  const toVerify = raw.slice(0, raw.length - 32);
  const providedHmac = raw.slice(raw.length - 32);

  const hmacKey = await crypto.subtle.importKey(
    "raw", signingKey, { name: "HMAC", hash: "SHA-256" }, false, ["verify"],
  );
  const valid = await crypto.subtle.verify("HMAC", hmacKey, providedHmac, toVerify);
  if (!valid) throw new Error("Fernet HMAC verification failed");

  const iv = raw.slice(1 + 8, 1 + 8 + 16);
  const ciphertext = raw.slice(1 + 8 + 16, raw.length - 32);

  const aesKey = await crypto.subtle.importKey(
    "raw", encryptionKey, { name: "AES-CBC" }, false, ["decrypt"],
  );
  const plainBuf = await crypto.subtle.decrypt({ name: "AES-CBC", iv }, aesKey, ciphertext);
  return new TextDecoder().decode(plainBuf);
}

// ── Token management ─────────────────────────────────────────────────────────

export interface GoogleTokenResult {
  accessToken: string;
  integrationTokenId: string;
}

/**
 * Load the Google access token for a client from integration_tokens.
 * Decrypts the stored refresh token, calls Google's token endpoint to get
 * a fresh access token, and updates integration_tokens with the new encrypted
 * access token — all atomically before returning.
 *
 * Requires CREDENTIALS_ENCRYPTION_KEY and GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET env vars.
 */
export async function getAccessToken(
  clientId: string,
  svc: SupabaseClient,
): Promise<GoogleTokenResult> {
  const encKey = Deno.env.get("CREDENTIALS_ENCRYPTION_KEY");
  const googleClientId = Deno.env.get("GOOGLE_CLIENT_ID");
  const googleClientSecret = Deno.env.get("GOOGLE_CLIENT_SECRET");

  if (!encKey) throw new Error("CREDENTIALS_ENCRYPTION_KEY not configured");
  if (!googleClientId || !googleClientSecret) {
    throw new Error("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not configured");
  }

  const { data: row, error } = await svc
    .from("integration_tokens")
    .select("id, refresh_token_encrypted, access_token_encrypted")
    .eq("client_id", clientId)
    .eq("provider", "google")
    .eq("is_default", true)
    .maybeSingle();

  if (error) throw new Error(`integration_tokens lookup failed: ${error.message}`);
  if (!row) throw new Error(`No Google token found for client ${clientId} — connect Google Drive first`);

  const integrationTokenId = row.id as string;
  const refreshTokenEncrypted = row.refresh_token_encrypted as string | null;

  if (!refreshTokenEncrypted) {
    throw new Error("Refresh token not stored — reconnect Google Drive with prompt=consent");
  }

  const refreshToken = await fernetDecrypt(encKey, refreshTokenEncrypted);

  // Exchange refresh token for a new access token
  const tokenResp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: refreshToken,
      client_id: googleClientId,
      client_secret: googleClientSecret,
    }),
  });

  if (!tokenResp.ok) {
    const body = await tokenResp.text();
    throw new Error(`Google token refresh failed (${tokenResp.status}): ${body}`);
  }

  const tokenData = await tokenResp.json() as { access_token: string; expires_in?: number };
  const accessToken = tokenData.access_token;

  if (!accessToken) throw new Error("Google token refresh returned no access_token");

  // Persist new access token (best-effort — do not fail the request if this fails)
  const { fernetEncrypt } = await importFernetEncrypt();
  try {
    const newAccessEncrypted = await fernetEncrypt(encKey, accessToken);
    await svc
      .from("integration_tokens")
      .update({ access_token_encrypted: newAccessEncrypted, updated_at: new Date().toISOString() })
      .eq("id", integrationTokenId);
  } catch (e) {
    console.warn("[google_drive] failed to persist refreshed access token:", e);
  }

  return { accessToken, integrationTokenId };
}

// Lazy import of fernetEncrypt to avoid circular dep; we duplicate the impl here.
async function importFernetEncrypt() {
  function base64urlEncode(bytes: Uint8Array): string {
    let binary = "";
    for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_");
  }
  function concatBytes(...arrays: Uint8Array[]): Uint8Array {
    const total = arrays.reduce((s, a) => s + a.length, 0);
    const out = new Uint8Array(total);
    let offset = 0;
    for (const arr of arrays) { out.set(arr, offset); offset += arr.length; }
    return out;
  }
  async function fernetEncrypt(keyBase64url: string, plaintext: string): Promise<string> {
    const keyBytes = base64urlDecode(keyBase64url);
    const signingKey = keyBytes.slice(0, 16);
    const encryptionKey = keyBytes.slice(16, 32);
    const ts = Math.floor(Date.now() / 1000);
    const timeBytes = new Uint8Array(8);
    const view = new DataView(timeBytes.buffer);
    view.setUint32(0, Math.floor(ts / 0x100000000), false);
    view.setUint32(4, ts >>> 0, false);
    const iv = crypto.getRandomValues(new Uint8Array(16));
    const aesKey = await crypto.subtle.importKey("raw", encryptionKey, { name: "AES-CBC" }, false, ["encrypt"]);
    const ciphertextBuf = await crypto.subtle.encrypt({ name: "AES-CBC", iv }, aesKey, new TextEncoder().encode(plaintext));
    const ciphertext = new Uint8Array(ciphertextBuf);
    const version = new Uint8Array([0x80]);
    const toSign = concatBytes(version, timeBytes, iv, ciphertext);
    const hmacKey = await crypto.subtle.importKey("raw", signingKey, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    const hmac = new Uint8Array(await crypto.subtle.sign("HMAC", hmacKey, toSign));
    return base64urlEncode(concatBytes(version, timeBytes, iv, ciphertext, hmac));
  }
  return { fernetEncrypt };
}

// ── Drive API helpers ────────────────────────────────────────────────────────

export interface DriveFileMetadata {
  id: string;
  name: string;
  mimeType: string;
  modifiedTime: string;
  size?: string;
}

const DRIVE_API = "https://www.googleapis.com/drive/v3";

/**
 * Fetch file metadata from Drive.
 * Always includes supportsAllDrives=true so Shared Drive files are found.
 */
export async function driveMetadata(
  accessToken: string,
  fileId: string,
): Promise<DriveFileMetadata> {
  const url = `${DRIVE_API}/files/${encodeURIComponent(fileId)}` +
    `?fields=id,name,mimeType,modifiedTime,size&supportsAllDrives=true&includeItemsFromAllDrives=true`;

  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Drive metadata failed (${resp.status}): ${body}`);
  }

  return resp.json() as Promise<DriveFileMetadata>;
}

// Supported MIME types and their handling strategy
const SUPPORTED_MIME_TYPES: Record<string, "export" | "download"> = {
  "application/vnd.google-apps.spreadsheet": "export",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "download",
  "application/vnd.ms-excel": "download",
  "text/csv": "download",
};

const XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

/**
 * Download or export a Drive file as a ReadableStream.
 *
 * - Google Sheets → exported as XLSX (Drive export endpoint)
 * - XLSX / XLS / CSV → direct download
 * - Other MIME types → throws with a clear error
 *
 * Returns the Response so the caller can stream the body directly into Storage
 * without buffering, avoiding edge function timeout on large files.
 */
export async function driveExportOrDownload(
  accessToken: string,
  fileId: string,
  mimeType: string,
): Promise<Response> {
  const strategy = SUPPORTED_MIME_TYPES[mimeType];
  if (!strategy) {
    throw new Error(
      `Unsupported file type: ${mimeType}. Only Google Sheets, Excel (.xlsx/.xls), and CSV files are supported.`,
    );
  }

  let url: string;
  if (strategy === "export") {
    // Export Google Sheets as XLSX
    url = `${DRIVE_API}/files/${encodeURIComponent(fileId)}/export` +
      `?mimeType=${encodeURIComponent(XLSX_MIME)}&supportsAllDrives=true`;
  } else {
    // Direct binary download
    url = `${DRIVE_API}/files/${encodeURIComponent(fileId)}?alt=media&supportsAllDrives=true&includeItemsFromAllDrives=true`;
  }

  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Drive download failed (${resp.status}): ${body}`);
  }

  return resp;
}

/**
 * Extract a Drive or Sheets file ID from a share URL.
 * Handles:
 *   https://drive.google.com/file/d/{id}/view
 *   https://docs.google.com/spreadsheets/d/{id}/edit
 *   https://drive.google.com/open?id={id}
 *   Bare file IDs (alphanumeric + dash/underscore, 25–44 chars)
 */
export function extractFileId(urlOrId: string): string | null {
  // /d/{id}/ pattern (Drive file URLs and Sheets URLs)
  const dPattern = /\/d\/([a-zA-Z0-9_-]{25,})/;
  const dMatch = urlOrId.match(dPattern);
  if (dMatch) return dMatch[1];

  // ?id={id} pattern
  const idPattern = /[?&]id=([a-zA-Z0-9_-]{25,})/;
  const idMatch = urlOrId.match(idPattern);
  if (idMatch) return idMatch[1];

  // Bare file ID
  if (/^[a-zA-Z0-9_-]{25,44}$/.test(urlOrId.trim())) return urlOrId.trim();

  return null;
}
