import "@testing-library/jest-dom/vitest";
import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReportsPage } from "@/features/reports/page";
import { reportsApi } from "@/features/reports/api";
import { reports as t } from "@/locales/reports";
import { ApiError } from "@/services/api-client";
vi.mock("next/navigation", () => ({ usePathname: () => "/admin/reports" }));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({ user: { id: "admin", role: "ADMIN" } }),
}));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
function mount() {
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { mutations: { retry: false } } })
      }
    >
      <ReportsPage />
    </QueryClientProvider>,
  );
}
it("prevents duplicate generation and submits selected type/format", async () => {
  vi.spyOn(reportsApi, "generate").mockImplementation(
    () => new Promise(() => {}),
  );
  mount();
  fireEvent.change(screen.getByLabelText(t.format), {
    target: { value: "xlsx" },
  });
  fireEvent.click(screen.getByRole("button", { name: t.generate }));
  expect(
    await screen.findByRole("button", { name: t.generating }),
  ).toBeDisabled();
  expect(reportsApi.generate).toHaveBeenCalledTimes(1);
  expect(reportsApi.generate).toHaveBeenCalledWith(
    { report_type: "inventory", format: "xlsx" },
    expect.anything(),
  );
});
it("safe generation failure never offers a download", async () => {
  vi.spyOn(reportsApi, "generate").mockRejectedValue(
    new ApiError(503, "REPORT_GENERATION_FAILED"),
  );
  mount();
  fireEvent.click(screen.getByRole("button", { name: t.generate }));
  expect(await screen.findByRole("alert")).toHaveTextContent(t.failed);
  expect(screen.queryByRole("link", { name: t.download })).toBeNull();
});
it("empty report explains the result and revokes private blob URLs on unmount", async () => {
  vi.spyOn(reportsApi, "generate").mockResolvedValue({
    blob: new Blob(["file"]),
    filename: "smartlibrary_inventory.pdf",
    rows: 0,
  });
  const create = vi.fn().mockReturnValue("blob:test"),
    revoke = vi.fn();
  vi.stubGlobal("URL", { createObjectURL: create, revokeObjectURL: revoke });
  mount();
  fireEvent.click(screen.getByRole("button", { name: t.generate }));
  expect(await screen.findByText(t.empty)).toBeVisible();
  await waitFor(() =>
    expect(screen.getByRole("link", { name: t.download })).toHaveAttribute(
      "href",
      "blob:test",
    ),
  );
  cleanup();
  expect(revoke).toHaveBeenCalledWith("blob:test");
});
