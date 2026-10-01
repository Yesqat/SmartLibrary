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
import { DirectIssue } from "@/features/circulation/direct-issue";
import { ReturnBook } from "@/features/circulation/return-book";
import { circulationApi, type Inventory } from "@/features/circulation/api";
import { circulation as t } from "@/locales/circulation";
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({ user: { role: "LIBRARIAN" } }),
}));
const inventory: Inventory = {
  book_id: "book",
  book_title: "Абай",
  physical_copy: {
    id: "copy",
    book_id: "book",
    inventory_number: "INV-1",
    shelf_location: "A-1",
    status: "BORROWED",
    condition: "GOOD",
    acquired_at: null,
    archived_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  active_borrowing: {
    id: "loan",
    user_id: "reader",
    book_copy_id: "copy",
    reservation_id: null,
    borrowed_at: "2026-01-01T00:00:00Z",
    due_at: "2026-01-15T00:00:00Z",
    returned_at: null,
    lost_at: null,
    status: "BORROWED",
    book_id: "book",
    book_title: "Абай",
    cover_url: null,
    inventory_number: "INV-1",
    reader_name: "Оқырман",
    is_overdue: true,
  },
};
function mount(ui: React.ReactNode) {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(<QueryClientProvider client={cache}>{ui}</QueryClientProvider>);
}
async function findCopy() {
  fireEvent.change(screen.getByRole("textbox", { name: t.inventory }), {
    target: { value: "INV-1" },
  });
  fireEvent.click(screen.getByRole("button", { name: t.findCopy }));
  await screen.findByRole("heading", { name: "Абай" });
}
beforeEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});
afterEach(cleanup);
it("physical return sends inspected condition only after confirmation and prevents repeats", async () => {
  vi.spyOn(circulationApi, "inventory").mockResolvedValue(inventory);
  vi.spyOn(circulationApi, "returnBook").mockImplementation(
    () => new Promise(() => {}),
  );
  vi.spyOn(window, "confirm").mockReturnValue(false);
  mount(<ReturnBook />);
  await findCopy();
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "DAMAGED" },
  });
  fireEvent.click(screen.getByRole("button", { name: t.returnBook }));
  expect(circulationApi.returnBook).not.toHaveBeenCalled();
  vi.mocked(window.confirm).mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: t.returnBook }));
  await waitFor(() =>
    expect(circulationApi.returnBook).toHaveBeenCalledWith("loan", "DAMAGED"),
  );
  await waitFor(() => expect(screen.getByRole("combobox")).toBeDisabled());
});
it("inventory without an active loan has no return/lost action", async () => {
  vi.spyOn(circulationApi, "inventory").mockResolvedValue({
    ...inventory,
    active_borrowing: null,
  });
  mount(<ReturnBook />);
  await findCopy();
  expect(screen.getByText(t.noLoan)).toBeVisible();
  expect(screen.queryByRole("button", { name: t.returnBook })).toBeNull();
  expect(screen.queryByRole("button", { name: t.lost })).toBeNull();
});
it("direct issue rejects unavailable stock in the UI and still delegates rules to the API", async () => {
  vi.spyOn(circulationApi, "inventory").mockResolvedValue(inventory);
  mount(<DirectIssue />);
  await findCopy();
  expect(screen.getByText(t.unavailable)).toBeVisible();
  expect(screen.queryByRole("button", { name: t.issue })).toBeNull();
});
it("a new inventory input clears the old actionable result", async () => {
  vi.spyOn(circulationApi, "inventory").mockResolvedValue(inventory);
  mount(<ReturnBook />);
  await findCopy();
  expect(screen.getByRole("button", { name: t.returnBook })).toBeVisible();
  fireEvent.change(screen.getByRole("textbox", { name: t.inventory }), {
    target: { value: "INV-2" },
  });
  expect(screen.queryByRole("button", { name: t.returnBook })).toBeNull();
});
