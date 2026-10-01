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
import { Pickup } from "@/features/circulation/pickup";
import { circulationApi, type PickupPreview } from "@/features/circulation/api";
import { circulation as t } from "@/locales/circulation";
import { ApiError } from "@/services/api-client";
import { librarianApi } from "@/features/librarian/api";
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({ user: { role: "LIBRARIAN" } }),
}));
const preview: PickupPreview = {
  reservation_id: "reservation",
  reservation_number: "R-1",
  reader_id: "reader",
  reader_name: "Оқырман",
  book_id: "book",
  book_title: "Абай",
  book_copy_id: "copy",
  inventory_number: "INV-1",
  shelf_location: "A-1",
  expires_at: "2099-01-01T00:00:00Z",
  verification_token: "test-boundary-proof",
  verification_expires_at: new Date(Date.now() + 600000).toISOString(),
};
function mount() {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={cache}>
      <Pickup />
    </QueryClientProvider>,
  );
}
async function submit() {
  fireEvent.change(screen.getByRole("textbox", { name: t.token }), {
    target: { value: "test-credential-at-the-api-boundary" },
  });
  fireEvent.click(screen.getByRole("button", { name: t.verify }));
}
beforeEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});
afterEach(cleanup);
it("manual reservation lookup previews only and uses the same separate issue action", async () => {
  vi.spyOn(librarianApi, "manual").mockResolvedValue(preview);
  vi.spyOn(circulationApi, "issueReserved").mockResolvedValue({} as never);
  mount();
  fireEvent.change(screen.getByLabelText("Бронь нөмірі"), {
    target: { value: "R-1" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Бронь нөмірімен тексеру" }),
  );
  expect(await screen.findByText(t.verified)).toBeVisible();
  expect(librarianApi.manual).toHaveBeenCalledWith("R-1");
  expect(circulationApi.issueReserved).not.toHaveBeenCalled();
  expect(screen.getByText("A-1")).toBeVisible();
});
it("verification only shows a preview; issuing needs a separate confirmed click", async () => {
  vi.spyOn(circulationApi, "verify").mockResolvedValue(preview);
  vi.spyOn(circulationApi, "issueReserved").mockImplementation(
    () => new Promise(() => {}),
  );
  vi.spyOn(window, "confirm").mockReturnValue(false);
  mount();
  await submit();
  expect(await screen.findByText(t.verified)).toBeVisible();
  expect(circulationApi.issueReserved).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: t.issue }));
  expect(circulationApi.issueReserved).not.toHaveBeenCalled();
  vi.mocked(window.confirm).mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: t.issue }));
  await waitFor(() =>
    expect(circulationApi.issueReserved).toHaveBeenCalledWith(
      preview.reservation_id,
      preview.verification_token,
    ),
  );
  await waitFor(() =>
    expect(screen.getByRole("button", { name: t.pending })).toBeDisabled(),
  );
});
it("invalid QR cannot expose an Issue control", async () => {
  vi.spyOn(circulationApi, "verify").mockRejectedValue(
    new ApiError(404, "INVALID_QR"),
  );
  mount();
  await submit();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "QR коды жарамсыз",
  );
  expect(screen.queryByRole("button", { name: t.issue })).toBeNull();
});
it("expired verification receipt requires re-verification", async () => {
  vi.spyOn(circulationApi, "verify").mockResolvedValue({
    ...preview,
    verification_expires_at: "2020-01-01T00:00:00Z",
  });
  mount();
  await submit();
  expect(await screen.findByRole("button", { name: t.issue })).toBeDisabled();
  expect(screen.getByText(t.reverify)).toBeVisible();
});
