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
import { ReserveButton } from "@/features/reservations/reserve-button";
import { ReservationList } from "@/features/reservations/list";
import { ReservationDetail } from "@/features/reservations/detail";
import { reservationApi, type Reservation } from "@/features/reservations/api";
import { reservations as t } from "@/locales/reservations";
import { ApiError } from "@/services/api-client";
import { safeReturnTo } from "@/features/auth/navigation";

const navigation = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => navigation }));
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "reader", role: "READER" },
  }),
}));
const row: Reservation = {
  id: "00000000-0000-0000-0000-000000000001",
  reservation_number: "R-100",
  book_id: "book",
  book_title: "Абай",
  book_copy_id: null,
  status: "WAITING",
  reserved_at: "2026-01-01T00:00:00Z",
  ready_at: null,
  expires_at: null,
  cancelled_at: null,
  completed_at: null,
  queue_position: 2,
  qr_available: false,
};
function mount(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});
afterEach(cleanup);

it("joins the queue through the real API boundary and prevents duplicate submission", async () => {
  vi.spyOn(reservationApi, "create").mockImplementation(
    () => new Promise(() => {}),
  );
  mount(<ReserveButton bookId="book" available={0} />);
  fireEvent.click(screen.getByRole("button", { name: t.wait }));
  await waitFor(() =>
    expect(reservationApi.create).toHaveBeenCalledWith("book"),
  );
  await waitFor(() =>
    expect(screen.getByRole("button", { name: t.loading })).toBeDisabled(),
  );
});
it("shows reservation errors without navigating", async () => {
  vi.spyOn(reservationApi, "create").mockRejectedValue(
    new ApiError(409, "RESERVATION_ALREADY_EXISTS"),
  );
  mount(<ReserveButton bookId="book" available={1} />);
  fireEvent.click(screen.getByRole("button", { name: t.reserve }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "белсенді броніңіз",
  );
  expect(navigation.push).not.toHaveBeenCalled();
});
it("renders empty history and sends the selected state to the backend", async () => {
  vi.spyOn(reservationApi, "list").mockResolvedValue({
    items: [],
    page: 1,
    page_size: 20,
    total: 0,
    pages: 0,
  });
  mount(<ReservationList />);
  expect(await screen.findByText(t.empty)).toBeVisible();
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "READY" },
  });
  await waitFor(() =>
    expect(reservationApi.list).toHaveBeenLastCalledWith(1, "READY", true),
  );
  fireEvent.click(screen.getByRole("button", { name: "Оқу тарихы" }));
  await waitFor(() =>
    expect(reservationApi.list).toHaveBeenLastCalledWith(1, "", false),
  );
  expect(screen.queryByRole("option", { name: "Алуға дайын" })).toBeNull();
});
it("waiting details never fetch QR and cancellation requires confirmation", async () => {
  vi.spyOn(reservationApi, "detail").mockResolvedValue(row);
  vi.spyOn(reservationApi, "qr");
  vi.spyOn(reservationApi, "cancel").mockResolvedValue({
    ...row,
    status: "CANCELLED",
  });
  vi.spyOn(window, "confirm").mockReturnValue(false);
  mount(<ReservationDetail id={row.id} />);
  fireEvent.click(await screen.findByRole("button", { name: t.cancel }));
  expect(reservationApi.cancel).not.toHaveBeenCalled();
  expect(reservationApi.qr).not.toHaveBeenCalled();
  expect(screen.queryByAltText(t.qr)).toBeNull();
  vi.mocked(window.confirm).mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: t.cancel }));
  await waitFor(() =>
    expect(reservationApi.cancel).toHaveBeenCalledWith(row.id),
  );
});
it("QR requires explicit display and expired READY never fetches it", async () => {
  vi.spyOn(reservationApi, "detail").mockResolvedValue({
    ...row,
    status: "READY",
    qr_available: false,
    expires_at: "2020-01-01T00:00:00Z",
  });
  vi.spyOn(reservationApi, "qr");
  mount(<ReservationDetail id={row.id} />);
  expect(await screen.findByText(t.expired)).toBeVisible();
  expect(reservationApi.qr).not.toHaveBeenCalled();
});
it("safe login destinations include book/owned reservation paths without open redirects", () => {
  expect(safeReturnTo(`/books/${row.id}`, "READER")).toBe(`/books/${row.id}`);
  expect(safeReturnTo(`/reservations/${row.id}`, "READER")).toBe(
    `/reservations/${row.id}`,
  );
  expect(safeReturnTo("//evil.example", "READER")).toBe("/dashboard");
  expect(safeReturnTo("/reservations", "ADMIN")).toBe("/admin");
});
