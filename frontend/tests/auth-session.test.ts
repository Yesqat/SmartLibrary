import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  apiRequest,
  checkSession,
  clearSession,
  getAuthState,
  login,
  refreshSession,
} from "@/services/api-client";
import { safeReturnTo } from "@/features/auth/navigation";

const user = {
  id: "reader",
  first_name: "Айдана",
  last_name: "Оқырман",
  email: "reader@example.com",
  phone: null,
  avatar_url: null,
  role: "READER",
  status: "ACTIVE",
  created_at: "2026-09-27T00:00:00Z",
};
const result = (token: string) => ({
  access_token: token,
  expires_in: 900,
  token_type: "bearer",
  user,
});
beforeEach(() => {
  clearSession();
  localStorage.clear();
  sessionStorage.clear();
});
afterEach(() => vi.unstubAllGlobals());

it("serializes concurrent restore requests and keeps credentials out of storage", async () => {
  const fetcher = vi
    .fn()
    .mockImplementation(async (path: string) =>
      Response.json(
        path.endsWith("csrf") ? { csrf_token: "proof" } : result("access"),
      ),
    );
  vi.stubGlobal("fetch", fetcher);
  await Promise.all([refreshSession(), refreshSession(), refreshSession()]);
  expect(
    fetcher.mock.calls.filter(([path]) => String(path).endsWith("refresh")),
  ).toHaveLength(1);
  expect(getAuthState().status).toBe("authenticated");
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
});
it("refreshes expired access once and retries with the new bearer", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(Response.json({ csrf_token: "proof" }))
    .mockResolvedValueOnce(Response.json(result("old")))
    .mockResolvedValueOnce(
      Response.json({ error: { code: "TOKEN_EXPIRED" } }, { status: 401 }),
    )
    .mockResolvedValueOnce(Response.json({ csrf_token: "proof2" }))
    .mockResolvedValueOnce(Response.json(result("new")))
    .mockResolvedValueOnce(Response.json(user));
  vi.stubGlobal("fetch", fetcher);
  await login({ email: user.email, password: "Not persisted password" });
  expect(await apiRequest("/auth/me")).toEqual(user);
  const headers = fetcher.mock.calls[5][1].headers as Headers;
  expect(headers.get("Authorization")).toBe("Bearer new");
});
it("clears identity when refresh is invalid", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce(Response.json({ csrf_token: "proof" }))
      .mockResolvedValueOnce(
        Response.json(
          { error: { code: "REFRESH_TOKEN_INVALID" } },
          { status: 401 },
        ),
      ),
  );
  expect(await refreshSession()).toBeNull();
  expect(getAuthState().status).toBe("anonymous");
});
it("shows unavailable state instead of pretending a network failure is logout", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new TypeError("network unavailable")),
  );
  await expect(refreshSession()).rejects.toThrow();
  expect(getAuthState().status).toBe("error");
});
it("does not resurrect identity from a response arriving after logout", async () => {
  let resolveResponse: (value: Response) => void = () => {};
  const late = new Promise<Response>((resolve) => {
    resolveResponse = resolve;
  });
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce(Response.json({ csrf_token: "proof" }))
      .mockResolvedValueOnce(Response.json(result("access")))
      .mockReturnValueOnce(late),
  );
  await login({ email: user.email, password: "Not persisted password" });
  const pending = checkSession();
  clearSession();
  resolveResponse(Response.json(user));
  await pending;
  expect(getAuthState().status).toBe("anonymous");
});
it("rejects external and wrong-role return destinations", () => {
  for (const target of [
    "https://evil.invalid",
    "//evil.invalid",
    "/admin",
    "/\\evil.invalid",
  ])
    expect(safeReturnTo(target, "READER")).toBe("/dashboard");
  expect(safeReturnTo("/account/security", "READER")).toBe("/account/security");
});
