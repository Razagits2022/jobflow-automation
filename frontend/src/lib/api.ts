/**
 * Typed axios API client.
 *
 * Reads the backend base URL from NEXT_PUBLIC_API_URL.
 * All feature modules import this client for data fetching.
 */
import axios from "axios";

const baseURL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 60_000,
});

/**
 * Quick ping to backend /health endpoint to check server availability
 * and trigger cold-start wakeup on Render free tier.
 */
export async function checkServerHealth(timeoutMs = 8_000): Promise<boolean> {
  try {
    const res = await axios.get(`${baseURL}/health`, {
      timeout: timeoutMs,
      headers: { "Cache-Control": "no-cache" },
    });
    return res.status === 200;
  } catch {
    return false;
  }
}

export function getApiBaseUrl(): string {
  return baseURL;
}

// ---------------------------------------------------------------------------
// Response interceptor — normalise errors into a consistent shape
// ---------------------------------------------------------------------------
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // TODO (Phase 2): add toast notifications for API errors
    return Promise.reject(error);
  }
);

// ---------------------------------------------------------------------------
// Typed helpers
// ---------------------------------------------------------------------------
export async function apiGet<T>(path: string): Promise<T> {
  const { data } = await apiClient.get<T>(path);
  return data;
}

export async function apiPost<T, B = unknown>(path: string, body: B): Promise<T> {
  const { data } = await apiClient.post<T>(path, body);
  return data;
}

export async function apiPatch<T, B = unknown>(path: string, body: B): Promise<T> {
  const { data } = await apiClient.patch<T>(path, body);
  return data;
}

export async function apiDelete(path: string): Promise<void> {
  await apiClient.delete(path);
}
