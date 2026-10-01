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
import { FavoriteButton } from "@/features/reader/favorites";
import { Notifications } from "@/features/reader/notifications";
import { LoanCard } from "@/features/reader/loans";
import { Profile } from "@/features/reader/profile";
import {
  readerApi,
  notificationLink,
  type Notification,
  type Loan,
} from "@/features/reader/api";
import { reader as t } from "@/locales/reader";
import * as session from "@/services/api-client";
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({ user: { role: "READER" } }),
}));
function mount(ui: React.ReactNode) {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(<QueryClientProvider client={cache}>{ui}</QueryClientProvider>);
}
beforeEach(() => vi.restoreAllMocks());
afterEach(cleanup);
const notification: Notification = {
  id: "n",
  type: "RESERVATION_READY",
  title: "Дайын",
  message: "Кітап дайын",
  is_read: false,
  related_entity_type: "RESERVATION",
  related_entity_id: "reservation",
  created_at: "2026-01-01T00:00:00Z",
};
it("favorite action uses current server state and prevents duplicate submission", async () => {
  vi.spyOn(readerApi, "favorite").mockResolvedValue({ is_favorite: false });
  vi.spyOn(readerApi, "setFavorite").mockImplementation(
    () => new Promise(() => {}),
  );
  mount(<FavoriteButton bookId="book" />);
  const button = screen.getByRole("button", { name: t.addFavorite });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
  await waitFor(() =>
    expect(readerApi.setFavorite).toHaveBeenCalledWith("book", true),
  );
  expect(button).toBeDisabled();
});
it("notification read action and navigation derive from controlled entity metadata", async () => {
  vi.spyOn(readerApi, "notifications").mockResolvedValue({
    items: [notification],
    total: 1,
    page: 1,
    page_size: 20,
    pages: 1,
  });
  vi.spyOn(readerApi, "read").mockResolvedValue({
    ...notification,
    is_read: true,
  });
  mount(<Notifications />);
  await screen.findByRole("heading", { name: "Дайын" });
  expect(screen.getByRole("link", { name: t.open })).toHaveAttribute(
    "href",
    "/reservations/reservation",
  );
  fireEvent.click(screen.getByRole("button", { name: t.read }));
  await waitFor(() => expect(readerApi.read).toHaveBeenCalledWith("n"));
  expect(
    notificationLink({ ...notification, related_entity_type: "BORROWING" }),
  ).toBe("/my-books");
});
it("Reader loan card displays overdue without offering physical return", () => {
  const loan: Loan = {
    id: "l",
    user_id: "u",
    book_copy_id: "c",
    reservation_id: null,
    book_id: "b",
    book_title: "Абай",
    cover_url: null,
    inventory_number: "INV",
    reader_name: "Reader",
    borrowed_at: "2026-01-01T00:00:00Z",
    due_at: "2026-01-15T00:00:00Z",
    returned_at: null,
    lost_at: null,
    status: "BORROWED",
    is_overdue: true,
  };
  mount(<LoanCard loan={loan} />);
  expect(screen.getByText(t.overdue)).toBeVisible();
  expect(screen.queryByRole("button")).toBeNull();
});
it("profile saves only names and phone, keeping email and role read-only", async () => {
  const user: session.User = {
    id: "u",
    first_name: "Аты",
    last_name: "Тегі",
    email: "reader@example.com",
    phone: null,
    avatar_url: null,
    role: "READER",
    status: "ACTIVE",
    created_at: "2026-01-01T00:00:00Z",
  };
  vi.spyOn(readerApi, "profile").mockResolvedValue(user);
  vi.spyOn(readerApi, "preferences").mockResolvedValue({ categories: [] });
  vi.spyOn(readerApi, "saveProfile").mockResolvedValue({
    ...user,
    first_name: "Айдана",
  });
  vi.spyOn(session, "checkSession").mockResolvedValue(user);
  mount(<Profile />);
  const name = await screen.findByLabelText(t.firstName);
  fireEvent.change(name, { target: { value: "Айдана" } });
  fireEvent.submit(name.closest("form")!);
  await waitFor(() =>
    expect(readerApi.saveProfile).toHaveBeenCalledWith(
      { first_name: "Айдана", last_name: "Тегі", phone: null },
      expect.anything(),
    ),
  );
  expect(screen.queryByRole("textbox", { name: t.email })).toBeNull();
  expect(screen.getByText(t.emailPolicy)).toBeVisible();
});
