import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Settings } from "@/features/admin/settings";
import { UserDetail } from "@/features/admin/user-detail";
import { Audit } from "@/features/admin/audit";
import { adminApi, type Setting } from "@/features/admin/api";
import type { User } from "@/services/api-client";
import { ApiError } from "@/services/api-client";
import { admin as t } from "@/locales/admin";
vi.mock("next/navigation", () => ({ usePathname: () => "/admin" }));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({ user: { id: "admin", role: "ADMIN" } }),
}));
const user: User = {
  id: "reader",
  first_name: "Айдана",
  last_name: "Омар",
  email: "reader@example.com",
  phone: null,
  avatar_url: null,
  role: "READER",
  status: "ACTIVE",
  created_at: "2026-01-01T00:00:00Z",
};
const settings: Setting[] = [
  {
    key: "max_books_per_user",
    value: 5,
    value_type: "INTEGER",
    minimum: 1,
    maximum: 100,
    description: "Limit",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    key: "block_borrowing_if_overdue",
    value: true,
    value_type: "BOOLEAN",
    minimum: null,
    maximum: null,
    description: "Overdue",
    updated_at: "2026-01-01T00:00:00Z",
  },
];
function mount(ui: React.ReactNode) {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(<QueryClientProvider client={cache}>{ui}</QueryClientProvider>);
  return cache;
}
beforeEach(() => vi.restoreAllMocks());
afterEach(cleanup);
it("rejects out-of-range, fractional and empty integer settings before submission", async () => {
  vi.spyOn(adminApi, "settings").mockResolvedValue(settings);
  vi.spyOn(adminApi, "saveSettings");
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mount(<Settings />);
  const input = await screen.findByLabelText(
    t.settingLabels.max_books_per_user,
  );
  for (const value of ["-1", "101", "1.5", ""]) {
    fireEvent.change(input, { target: { value } });
    expect((input as HTMLInputElement).checkValidity()).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: t.save }));
    expect(adminApi.saveSettings).not.toHaveBeenCalled();
  }
});
it("privilege edits require confirmation and submit only the selected role", async () => {
  vi.spyOn(adminApi, "user").mockResolvedValue(user);
  vi.spyOn(adminApi, "role").mockResolvedValue({ ...user, role: "LIBRARIAN" });
  vi.spyOn(window, "confirm").mockReturnValue(false);
  mount(<UserDetail id="reader" />);
  fireEvent.change(await screen.findByLabelText(t.role), {
    target: { value: "LIBRARIAN" },
  });
  fireEvent.click(screen.getByRole("button", { name: t.changeRole }));
  expect(adminApi.role).not.toHaveBeenCalled();
  vi.mocked(window.confirm).mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: t.changeRole }));
  await waitFor(() =>
    expect(adminApi.role).toHaveBeenCalledWith("reader", "LIBRARIAN"),
  );
});
it("settings save only dirty values with original versions and require confirmation", async () => {
  vi.spyOn(adminApi, "settings").mockResolvedValue(settings);
  vi.spyOn(adminApi, "saveSettings").mockImplementation(
    () => new Promise(() => {}),
  );
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const cache = mount(<Settings />);
  const input = await screen.findByLabelText(
    t.settingLabels.max_books_per_user,
  );
  fireEvent.change(input, { target: { value: "7" } });
  cache.setQueryData(
    ["admin-settings"],
    settings.map((row) => ({ ...row, updated_at: "2026-02-01T00:00:00Z" })),
  );
  fireEvent.click(screen.getByRole("button", { name: t.save }));
  await waitFor(() =>
    expect(adminApi.saveSettings).toHaveBeenCalledWith([
      {
        key: "max_books_per_user",
        value: 7,
        expected_updated_at: settings[0].updated_at,
      },
    ]),
  );
  expect(input).toBeDisabled();
});
it("stale settings show a safe conflict error without a fabricated success", async () => {
  vi.spyOn(adminApi, "settings").mockResolvedValue(settings);
  vi.spyOn(adminApi, "saveSettings").mockRejectedValue(
    new ApiError(409, "SETTINGS_CONFLICT"),
  );
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mount(<Settings />);
  fireEvent.change(
    await screen.findByLabelText(t.settingLabels.max_books_per_user),
    { target: { value: "7" } },
  );
  fireEvent.click(screen.getByRole("button", { name: t.save }));
  expect(await screen.findByRole("alert")).toHaveTextContent("басқа терезеде");
  expect(screen.queryByText(t.saved)).toBeNull();
});
it("audit view renders safe summaries and offers no edit or delete control", async () => {
  vi.spyOn(adminApi, "audit").mockResolvedValue({
    items: [
      {
        id: "event",
        user_id: "admin",
        actor_name: "Әкімші",
        action: "ROLE_CHANGED",
        entity_type: "USER",
        entity_id: "reader",
        details: { reason: "READER->LIBRARIAN" },
        created_at: "2026-01-01T00:00:00Z",
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
    pages: 1,
  });
  mount(<Audit />);
  expect(await screen.findByText("READER->LIBRARIAN")).toBeVisible();
  expect(
    screen.queryByRole("button", { name: /Өшіру|Жою|Өзгерту/ }),
  ).toBeNull();
});
