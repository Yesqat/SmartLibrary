import "@testing-library/jest-dom/vitest";
import { StrictMode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  act,
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
import { recordCreationFeedback } from "@/features/reservations/creation-feedback";
import { catalogApi, type Book } from "@/features/catalog/api";
import { reservations as t } from "@/locales/reservations";
import { kk } from "@/locales/kk";
import { ApiError } from "@/services/api-client";
import { safeReturnTo } from "@/features/auth/navigation";

const navigation = vi.hoisted(() => ({ push: vi.fn() }));
const auth = vi.hoisted(() => ({
  status: "authenticated",
  user: { id: "reader", role: "READER" },
}));
vi.mock("next/navigation", () => ({ useRouter: () => navigation }));
vi.mock("@/features/auth/auth-provider", () => ({ useAuth: () => auth }));
vi.mock("@/services/api-client", async (original) => ({
  ...(await original<typeof import("@/services/api-client")>()),
  getAuthState: () => auth,
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
const book: Book = {
  id: row.book_id,
  title: row.book_title,
  authors: [],
  categories: [],
  language: "kk",
  isbn: null,
  description: null,
  publisher: null,
  cover_url: "/covers/test.jpg",
  page_count: null,
  publication_year: null,
  archived_at: null,
  created_at: row.reserved_at,
  updated_at: row.reserved_at,
  available_copies: 1,
  total_copies: 1,
  shelf_locations: [],
};
const markerKey = ["reservation-created-feedback", "reader", row.id];
const ready = (): Reservation => ({
  ...row,
  status: "READY",
  qr_available: true,
  queue_position: null,
  expires_at: new Date(Date.now() + 60_000).toISOString(),
});
function queryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}
function mount(ui: React.ReactNode, client = queryClient()) {
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
  auth.user = { id: "reader", role: "READER" };
  vi.spyOn(catalogApi, "book").mockResolvedValue({ ...book, cover_url: null });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("joins the queue through the real API boundary and prevents duplicate submission", async () => {
  vi.spyOn(reservationApi, "create").mockImplementation(
    () => new Promise(() => {}),
  );
  const client = queryClient();
  mount(<ReserveButton bookId="book" available={0} />, client);
  const button = screen.getByRole("button", { name: t.wait });
  act(() => {
    button.click();
    button.click();
  });
  await waitFor(() =>
    expect(reservationApi.create).toHaveBeenCalledWith("book"),
  );
  await waitFor(() =>
    expect(screen.getByRole("button", { name: t.loading })).toBeDisabled(),
  );
  expect(reservationApi.create).toHaveBeenCalledTimes(1);
  expect(client.getQueryData(markerKey)).toBeUndefined();
  expect(navigation.push).not.toHaveBeenCalled();
});
it.each([
  [409, "RESERVATION_ALREADY_EXISTS", "белсенді броніңіз"],
  [500, "REQUEST_FAILED", kk.error],
] as const)(
  "shows reservation error %i without navigating",
  async (status, code, message) => {
    vi.spyOn(reservationApi, "create").mockRejectedValue(
      new ApiError(status, code),
    );
    const client = queryClient();
    mount(<ReserveButton bookId="book" available={1} />, client);
    fireEvent.click(screen.getByRole("button", { name: t.reserve }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(navigation.push).not.toHaveBeenCalled();
    expect(client.getQueryData(markerKey)).toBeUndefined();
  },
);

it("opens the saved reservation even when writing its feedback marker fails", async () => {
  vi.spyOn(reservationApi, "create").mockResolvedValue(row);
  const cache = queryClient();
  const write = vi.spyOn(cache, "setQueryData").mockImplementationOnce(() => {
    throw new Error("Feedback unavailable");
  });
  mount(<ReserveButton bookId={row.book_id} available={0} />, cache);
  fireEvent.click(screen.getByRole("button", { name: t.wait }));
  await waitFor(() =>
    expect(navigation.push.mock.calls).toEqual([[`/reservations/${row.id}`]]),
  );
  expect(write.mock.calls[0][0]).toEqual(markerKey);
  expect(screen.queryByRole("alert")).toBeNull();
  expect(cache.getQueryData(markerKey)).toBeUndefined();
});

it.each(["READY", "WAITING"] as const)(
  "confirms server status %s after navigation even when availability suggested the opposite",
  async (status) => {
    const reservation = status === "READY" ? ready() : row;
    vi.spyOn(reservationApi, "create").mockResolvedValue(reservation);
    vi.spyOn(reservationApi, "detail").mockResolvedValue(reservation);
    const qr = vi.spyOn(reservationApi, "qr").mockResolvedValue({
      token: "private",
      image_data_url: "data:image/png;base64,AA==",
      expires_at: reservation.expires_at!,
    });
    const cache = queryClient();
    const refresh = Promise.withResolvers<void>();
    const invalidate = vi
      .spyOn(cache, "invalidateQueries")
      .mockResolvedValue(undefined)
      .mockReturnValueOnce(refresh.promise);
    const button = mount(
      <ReserveButton
        bookId={row.book_id}
        available={status === "READY" ? 0 : 1}
      />,
      cache,
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: status === "READY" ? t.wait : t.reserve,
      }),
    );
    await waitFor(() => expect(invalidate).toHaveBeenCalledTimes(7));
    expect(invalidate.mock.calls.map(([filter]) => filter?.queryKey)).toEqual([
      ["catalog"],
      ["recommendations"],
      ["search"],
      ["reservations"],
      ["reader-summary"],
      ["notifications"],
      ["favorites"],
    ]);
    expect(navigation.push).not.toHaveBeenCalled();
    expect(screen.getByRole("button")).toBeDisabled();
    await act(async () => refresh.resolve());
    await waitFor(() =>
      expect(navigation.push.mock.calls).toEqual([[`/reservations/${row.id}`]]),
    );
    expect(cache.getQueryData(markerKey)).toEqual({
      reservationId: row.id,
      bookId: row.book_id,
      userId: "reader",
      createdAt: expect.any(Number),
    });

    button.unmount();
    const detail = mount(
      <StrictMode>
        <ReservationDetail id={row.id} />
      </StrictMode>,
      cache,
    );
    const message = await screen.findByText(
      status === "READY" ? t.createdReady : t.createdWaiting,
    );
    expect(message.closest('[role="status"]')).toBeVisible();
    expect(cache.getQueryData(markerKey)).toBeUndefined();
    expect(document.querySelector("[data-reservation-ribbon]")).toBeNull();
    expect(qr).not.toHaveBeenCalled();
    if (status === "READY") {
      fireEvent.click(screen.getByRole("button", { name: t.showQR }));
      expect(await screen.findByRole("img", { name: t.qr })).toBeVisible();
      expect(qr).toHaveBeenCalledWith(row.id);
    } else {
      expect(screen.getByText(t.queueNote)).toBeVisible();
      expect(screen.queryByRole("button", { name: t.showQR })).toBeNull();
    }

    detail.unmount();
    mount(<ReservationDetail id={row.id} />, cache);
    await screen.findByText(row.reservation_number);
    expect(screen.queryByText(t.createdReady)).toBeNull();
    expect(screen.queryByText(t.createdWaiting)).toBeNull();
  },
);

it.each(["create", "cache refresh"])(
  "does not leave feedback for a different reader when identity changes during %s",
  async (stage) => {
    const create = Promise.withResolvers<Reservation>();
    const refresh = Promise.withResolvers<void>();
    vi.spyOn(reservationApi, "create").mockReturnValue(create.promise);
    const cache = queryClient();
    const invalidate = vi
      .spyOn(cache, "invalidateQueries")
      .mockReturnValue(refresh.promise);
    mount(<ReserveButton bookId={row.book_id} available={1} />, cache);
    fireEvent.click(screen.getByRole("button", { name: t.reserve }));
    await waitFor(() => expect(reservationApi.create).toHaveBeenCalled());
    if (stage === "cache refresh") {
      await act(async () => create.resolve(row));
      await waitFor(() => expect(invalidate).toHaveBeenCalledTimes(7));
    }
    auth.user = { ...auth.user, id: "next-reader" };
    cache.clear(); // AuthProvider clears its shared QueryClient on identity changes.
    await act(async () => {
      create.resolve(row);
      refresh.resolve();
    });
    expect(
      cache.getQueriesData({ queryKey: ["reservation-created-feedback"] }),
    ).toHaveLength(0);
  },
);
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
  const cache = queryClient();
  const credentialKey = ["reservation-credential", row.id];
  cache.setQueryData(credentialKey, { token: "test-only" });
  mount(<ReservationDetail id={row.id} />, cache);
  fireEvent.click(await screen.findByRole("button", { name: t.cancel }));
  expect(reservationApi.cancel).not.toHaveBeenCalled();
  expect(reservationApi.qr).not.toHaveBeenCalled();
  expect(screen.queryByAltText(t.qr)).toBeNull();
  expect(cache.getQueryData(credentialKey)).toBeDefined();
  vi.mocked(window.confirm).mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: t.cancel }));
  await waitFor(() =>
    expect(reservationApi.cancel).toHaveBeenCalledWith(row.id),
  );
  await waitFor(() =>
    expect(cache.getQueryData(credentialKey)).toBeUndefined(),
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

it.each([
  "direct visit",
  "wrong user",
  "wrong reservation",
  "wrong book",
  "expired marker",
  "expired pickup",
  "expired on the server",
  "CANCELLED",
  "COMPLETED",
  "EXPIRED",
])("keeps the detail page free of creation feedback for %s", async (reason) => {
  const cache = queryClient();
  let response = row;
  if (reason !== "direct visit") recordCreationFeedback(cache, "reader", row);
  if (reason === "wrong user") auth.user = { ...auth.user, id: "other" };
  if (reason === "wrong reservation")
    response = { ...row, id: "another-reservation" };
  if (reason === "wrong book") response = { ...row, book_id: "another-book" };
  if (reason === "expired marker")
    cache.setQueryData(markerKey, {
      reservationId: row.id,
      userId: "reader",
      bookId: row.book_id,
      createdAt: Date.now() - 30_001,
    });
  if (reason === "expired pickup")
    response = {
      ...ready(),
      expires_at: new Date(Date.now() - 1).toISOString(),
    };
  if (reason === "expired on the server")
    response = { ...ready(), qr_available: false };
  if (reason === "CANCELLED" || reason === "COMPLETED" || reason === "EXPIRED")
    response = { ...row, status: reason };
  vi.spyOn(reservationApi, "detail").mockResolvedValue(response);
  mount(<ReservationDetail id={response.id} />, cache);
  await screen.findByText(row.reservation_number);
  expect(screen.queryByText(t.createdReady)).toBeNull();
  expect(screen.queryByText(t.createdWaiting)).toBeNull();
  expect(document.querySelector("[data-reservation-ribbon]")).toBeNull();
  if (reason !== "wrong user" && reason !== "wrong reservation")
    expect(cache.getQueryData(markerKey)).toBeUndefined();
});

it("discards a pending detail visit and never replays creation on later visits or promotion", async () => {
  const cache = queryClient();
  recordCreationFeedback(cache, "reader", row);
  const first = Promise.withResolvers<Reservation>();
  const detail = vi
    .spyOn(reservationApi, "detail")
    .mockReturnValueOnce(first.promise)
    .mockResolvedValueOnce(row)
    .mockResolvedValue(ready());
  const visit = mount(<ReservationDetail id={row.id} />, cache);
  await waitFor(() => expect(detail).toHaveBeenCalledWith(row.id));
  visit.unmount();
  await act(async () => first.resolve(row));
  mount(<ReservationDetail id={row.id} />, cache);
  expect(await screen.findByText(t.queueNote)).toBeVisible();
  expect(screen.queryByText(t.createdWaiting)).toBeNull();
  await act(async () => {
    await cache.invalidateQueries({ queryKey: ["reservations", row.id] });
  });
  expect(await screen.findByRole("button", { name: t.showQR })).toBeVisible();
  expect(screen.queryByText(t.createdReady)).toBeNull();
  expect(document.querySelector("[data-reservation-ribbon]")).toBeNull();
});

it.each(["loaded", "reduced motion", "failed", "measurement fails"])(
  "confirms once in StrictMode when the actual cover is %s",
  async (mode) => {
    vi.stubGlobal("matchMedia", () => ({
      matches: mode === "reduced motion",
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    const cache = queryClient();
    recordCreationFeedback(cache, "reader", row);
    cache.setQueryData(["catalog", "book", row.book_id], book);
    cache.setQueryData(["reservations", row.id], row);
    vi.mocked(catalogApi.book).mockResolvedValue(book);
    const fresh = Promise.withResolvers<Reservation>();
    vi.spyOn(reservationApi, "detail").mockReturnValue(fresh.promise);
    mount(
      <StrictMode>
        <ReservationDetail id={row.id} />
      </StrictMode>,
      cache,
    );
    const source = await screen.findByRole("img", { name: row.book_title });
    if (mode === "failed") fireEvent.error(source);
    else {
      Object.assign(source.style, {
        width: "120px",
        height: "180px",
        padding: "6px",
      });
      Object.defineProperties(source, {
        complete: { value: true },
        naturalWidth: { value: 400 },
        naturalHeight: { value: 600 },
      });
      const bounds = vi
        .spyOn(source, "getBoundingClientRect")
        .mockReturnValue(new DOMRect(40, 100, 120, 180));
      if (mode === "measurement fails")
        bounds.mockImplementation(() => {
          throw new Error("No artwork bounds");
        });
    }
    expect(screen.queryByText(t.createdWaiting)).toBeNull();
    await act(async () => fresh.resolve(row));
    expect(await screen.findByText(t.createdWaiting)).toBeVisible();
    const ribbons = document.querySelectorAll("[data-reservation-ribbon]");
    expect(ribbons).toHaveLength(mode === "loaded" ? 1 : 0);
    if (mode === "loaded") {
      expect(ribbons[0]).toHaveAttribute("aria-hidden", "true");
      expect(source).toBeVisible();
      fireEvent(window, new Event("resize"));
      expect(document.querySelector("[data-reservation-ribbon]")).toBeNull();
      expect(screen.getByText(t.createdWaiting)).toBeVisible();
    }
    expect(catalogApi.book).toHaveBeenCalledTimes(1);
    expect(cache.getQueryData(markerKey)).toBeUndefined();
  },
);
it("safe login destinations include book/owned reservation paths without open redirects", () => {
  expect(safeReturnTo(`/books/${row.id}`, "READER")).toBe(`/books/${row.id}`);
  expect(safeReturnTo(`/reservations/${row.id}`, "READER")).toBe(
    `/reservations/${row.id}`,
  );
  expect(safeReturnTo("//evil.example", "READER")).toBe("/dashboard");
  expect(safeReturnTo("/reservations", "ADMIN")).toBe("/admin");
});
