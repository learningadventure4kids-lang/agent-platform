/** Shared fetch wrapper for every API client in this app (admin
 * dashboard: client.ts, self-serve builder: customer.ts). Pulled out so
 * the header-ordering fix below -- which has bitten this project once
 * already in production -- lives in exactly one place instead of two
 * copies that could drift back out of sync. */

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/** FastAPI returns `detail` as a plain string for most errors, but as an
 * ARRAY of Pydantic validation-error objects (`{loc, msg, type}`) for 422
 * request-body validation failures. Passing that array straight into
 * `Error(message)` gets silently coerced to the string "[object Object]"
 * by JavaScript -- this normalizes every shape into one readable string
 * instead. */
export function extractErrorDetail(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object" || !("detail" in body)) return fallback;
  const detail = (body as { detail: unknown }).detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        const loc = Array.isArray((item as { loc?: unknown[] }).loc)
          ? (item as { loc: unknown[] }).loc.filter((l) => l !== "body").join(".")
          : "";
        const msg = String((item as { msg: unknown }).msg);
        return loc ? `${loc}: ${msg}` : msg;
      }
      return typeof item === "string" ? item : JSON.stringify(item);
    });
    return messages.join("; ") || fallback;
  }

  if (detail && typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }

  return fallback;
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  // A FormData body (file uploads) must NOT get a Content-Type default --
  // the browser needs to set its own "multipart/form-data; boundary=..."
  // header, which only happens if Content-Type is left unset entirely.
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      // IMPORTANT: this must come AFTER `...options`, not before -- object
      // literals let a later key win, so spreading `options` first and
      // setting `headers` last is what makes the Content-Type default
      // actually merge with (rather than get silently replaced by) each
      // call's own headers (e.g. `authHeaders(adminKey)`). Getting this
      // backwards means every authenticated request loses its
      // "Content-Type: application/json" header, the browser falls back to
      // "text/plain" for the string body, and FastAPI then hands Pydantic
      // the raw JSON *string* instead of parsing it -- producing the
      // (very confusing) "Input should be a valid dictionary or object to
      // extract fields from" error on every save.
      headers: isFormData ? options.headers : { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new ApiError("Can't reach the server right now.", 0);
  }
  if (!res.ok) {
    let detail = "Something went wrong.";
    try {
      detail = extractErrorDetail(await res.json(), detail);
    } catch {
      /* ignore -- response body wasn't JSON */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
