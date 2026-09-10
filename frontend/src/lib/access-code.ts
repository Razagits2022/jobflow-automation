/**
 * Access Code Manager for JobFlow
 *
 * Enforces 30-day client-side access control.
 * Validates against NEXT_PUBLIC_ACCESS_CODE (with sensible fallback codes).
 */

export const ACCESS_STORAGE_KEY = "jobflow_access_pass";
export const ACCESS_EXPIRY_DAYS = 30;
export const ACCESS_EXPIRY_MS = ACCESS_EXPIRY_DAYS * 24 * 60 * 60 * 1000;

export const DEFAULT_ACCESS_CODES = [
  "JOBFLOW2026",
  "JOBFLOW-VIP",
  "ACCESS2026",
  "AUTOPILOT2026",
];

export interface AccessPass {
  code: string;
  grantedAt: number;
  expiresAt: number;
}

/**
 * Returns the list of permitted access codes.
 * Reads NEXT_PUBLIC_ACCESS_CODE (comma-separated supported) and includes defaults.
 */
export function getAllowedAccessCodes(): string[] {
  const envCodes = process.env.NEXT_PUBLIC_ACCESS_CODE
    ? process.env.NEXT_PUBLIC_ACCESS_CODE.split(",").map((c) => c.trim())
    : [];

  const combined = [...envCodes, ...DEFAULT_ACCESS_CODES];
  return Array.from(new Set(combined.map((c) => c.toUpperCase())));
}

/**
 * Checks if a given input string matches any permitted access code (case-insensitive).
 */
export function isValidCode(input: string): boolean {
  if (!input) return false;
  const normalized = input.trim().toUpperCase();
  const allowed = getAllowedAccessCodes();
  return allowed.includes(normalized);
}

/**
 * Reads and validates the current access pass from localStorage.
 * Automatically cleans up expired or invalid passes.
 */
export function getStoredAccessPass(): AccessPass | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(ACCESS_STORAGE_KEY);
    if (!raw) return null;

    const pass = JSON.parse(raw) as AccessPass;
    if (!pass || typeof pass.expiresAt !== "number" || !pass.code) {
      window.localStorage.removeItem(ACCESS_STORAGE_KEY);
      return null;
    }

    // Check 30-day expiration
    if (Date.now() >= pass.expiresAt) {
      window.localStorage.removeItem(ACCESS_STORAGE_KEY);
      return null;
    }

    // Check code validity
    if (!isValidCode(pass.code)) {
      window.localStorage.removeItem(ACCESS_STORAGE_KEY);
      return null;
    }

    return pass;
  } catch {
    return null;
  }
}

/**
 * Returns true if the user currently holds a valid, unexpired access pass.
 */
export function hasValidAccess(): boolean {
  return getStoredAccessPass() !== null;
}

/**
 * Grants access for 30 days if the provided code is valid.
 */
export function grantAccess(code: string): { success: boolean; error?: string } {
  if (typeof window === "undefined") {
    return { success: false, error: "Window is unavailable" };
  }

  const trimmed = (code || "").trim();
  if (!trimmed) {
    return { success: false, error: "Please enter an access code." };
  }

  if (!isValidCode(trimmed)) {
    return {
      success: false,
      error: "Invalid access code. Please check with your administrator.",
    };
  }

  const now = Date.now();
  const pass: AccessPass = {
    code: trimmed.toUpperCase(),
    grantedAt: now,
    expiresAt: now + ACCESS_EXPIRY_MS,
  };

  try {
    window.localStorage.setItem(ACCESS_STORAGE_KEY, JSON.stringify(pass));
    window.dispatchEvent(new Event("jobflow-access-changed"));
    return { success: true };
  } catch {
    return {
      success: false,
      error: "Failed to save access code. Please ensure storage is enabled.",
    };
  }
}

/**
 * Revokes the current access pass and notifies the application.
 */
export function revokeAccess(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(ACCESS_STORAGE_KEY);
    window.dispatchEvent(new Event("jobflow-access-changed"));
  } catch {
    // Ignore error
  }
}

/**
 * Returns the number of remaining days for the current access pass.
 */
export function getRemainingDays(): number {
  const pass = getStoredAccessPass();
  if (!pass) return 0;
  const msLeft = pass.expiresAt - Date.now();
  return Math.max(0, Math.ceil(msLeft / (24 * 60 * 60 * 1000)));
}
