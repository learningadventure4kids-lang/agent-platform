/**
 * Regression guard for a bug introduced (and caught before shipping) while
 * adding the self-serve builder's document upload: `request()`'s default
 * `Content-Type: application/json` header must NOT be applied to a
 * FormData body (file uploads) -- doing so stops the browser from setting
 * its own `multipart/form-data; boundary=...` header, and the backend
 * then fails to parse the upload at all. JSON bodies must still get the
 * default.
 */
import { describe, expect, it, vi } from "vitest";

describe("request() Content-Type handling", () => {
  it("does not force application/json onto a FormData body", async () => {
    const capturedInit: RequestInit[] = [];
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      capturedInit.push(init);
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { request } = await import("../src/api/http");
    const form = new FormData();
    form.append("file", new Blob(["hello"]), "hello.txt");
    await request("/api/builder/agents/1/documents", {
      method: "POST",
      headers: { Authorization: "Bearer usess_test" },
      body: form,
    });

    const headers = capturedInit[0].headers as Record<string, string>;
    expect(headers["Content-Type"]).toBeUndefined();
    expect(headers["Authorization"]).toBe("Bearer usess_test");
    expect(capturedInit[0].body).toBeInstanceOf(FormData);

    vi.unstubAllGlobals();
  });

  it("still defaults a JSON body to application/json", async () => {
    const capturedInit: RequestInit[] = [];
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      capturedInit.push(init);
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { request } = await import("../src/api/http");
    await request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: "a@b.com", password: "x" }),
    });

    const headers = capturedInit[0].headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");

    vi.unstubAllGlobals();
  });
});
