/**
 * Regression test for a real production bug: `request()`'s fetch options
 * object used to spread `...options` AFTER setting `headers`, which meant
 * any call passing its own `headers` (e.g. `authHeaders(adminKey)`, used
 * by every admin-authenticated request) silently wiped out the
 * "Content-Type: application/json" default entirely. Without it, the
 * browser sends a JSON string body as `text/plain`, and FastAPI hands
 * Pydantic the raw JSON *string* instead of parsing it -- producing the
 * (very confusing) "Input should be a valid dictionary or object to
 * extract fields from" error on every authenticated save.
 *
 * This test doesn't need a running backend -- it just proves the fetch
 * options object this module builds always has both headers merged,
 * regardless of what a caller passes in `options.headers`.
 */
import { describe, expect, it, vi } from "vitest";

describe("admin client request() header merging", () => {
  it("keeps Content-Type when the caller also passes custom headers", async () => {
    const capturedInit: RequestInit[] = [];
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      capturedInit.push(init);
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const client = await import("../src/api/client");
    await client.updateAgent("secret-admin-key", 1, { name: "Test" });

    expect(capturedInit).toHaveLength(1);
    const headers = capturedInit[0].headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");
    expect(headers["X-Admin-Key"]).toBe("secret-admin-key");

    vi.unstubAllGlobals();
  });
});
