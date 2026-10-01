import { afterEach, expect, it, vi } from "vitest";
import { apiRequest, apiDownload, ApiError } from "@/services/api-client";
afterEach(() => vi.unstubAllGlobals());
it("binary downloads preserve bytes and only accept safe server filenames", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response("%PDF-real", {
        headers: {
          "Content-Disposition":
            'attachment; filename="smartlibrary_inventory.pdf"',
          "X-Report-Rows": "2",
        },
      }),
    ),
  );
  const result = await apiDownload("/admin/reports", {
    report_type: "inventory",
    format: "pdf",
  });
  expect(await result.blob.text()).toBe("%PDF-real");
  expect(result.filename).toBe("smartlibrary_inventory.pdf");
  expect(result.rows).toBe(2);
});
it("uses versioned same-origin requests and preserves cancellation", async () => {
  const fetcher = vi.fn().mockResolvedValue(Response.json({ status: "ok" }));
  vi.stubGlobal("fetch", fetcher);
  const signal = new AbortController().signal;
  expect(await apiRequest("/health", { signal })).toEqual({ status: "ok" });
  expect(fetcher).toHaveBeenCalledWith(
    "/api/v1/health",
    expect.objectContaining({ signal, credentials: "same-origin" }),
  );
});
it("hides unsafe backend error messages", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json(
          { error: { code: "INTERNAL_ERROR", message: "secret" } },
          { status: 500 },
        ),
      ),
  );
  const error = await apiRequest("/health").catch((e: unknown) => e);
  expect(error).toBeInstanceOf(ApiError);
  expect((error as Error).message).not.toContain("secret");
});
it("rejects external URL paths before any request", async () => {
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  await expect(apiRequest("//external.invalid")).rejects.toThrow();
  expect(fetcher).not.toHaveBeenCalled();
});
