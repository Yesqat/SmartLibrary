import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CatalogList } from "@/features/catalog/catalog-list";
import { BookDetail } from "@/features/catalog/book-detail";
import { BookEditor } from "@/features/catalog/book-editor";
import { catalogApi, type Book } from "@/features/catalog/api";
import { apiMutation, ApiError, clearSession } from "@/services/api-client";
import { catalog as t } from "@/locales/catalog";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/services/api-client", async (original) => ({
  ...(await original<typeof import("@/services/api-client")>()),
  apiMutation: vi.fn(),
}));
const book: Book = {
  id: "00000000-0000-0000-0000-000000000001",
  title: "Абай жолы",
  isbn: null,
  description: "Роман",
  publication_year: 1942,
  language: "kk",
  page_count: 300,
  cover_url: null,
  publisher: null,
  authors: [],
  categories: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  archived_at: null,
  total_copies: 3,
  available_copies: 0,
  shelf_locations: [],
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
  clearSession();
});
afterEach(cleanup);

it("shows actual zero availability and a book link", async () => {
  vi.spyOn(catalogApi, "books").mockResolvedValue({
    items: [book],
    page: 1,
    page_size: 20,
    pages: 1,
    total: 1,
  });
  mount(<CatalogList />);
  expect(await screen.findByRole("heading", { name: book.title })).toBeTruthy();
  expect(screen.getByText(`${t.available}: 0 / 3`)).toBeTruthy();
  expect(
    screen.getByRole("link", { name: book.title }).getAttribute("href"),
  ).toBe(`/books/${book.id}`);
});
it("renders an empty response and sends search to the API", async () => {
  const list = vi.spyOn(catalogApi, "books").mockResolvedValue({
    items: [],
    page: 1,
    page_size: 20,
    pages: 0,
    total: 0,
  });
  mount(<CatalogList />);
  expect(await screen.findByText(t.empty)).toBeTruthy();
  fireEvent.change(screen.getByRole("textbox", { name: t.search }), {
    target: { value: "Ғылым" },
  });
  fireEvent.click(screen.getByRole("button", { name: t.find }));
  await waitFor(() => expect(list).toHaveBeenLastCalledWith(1, "Ғылым", false));
});
it("shows a safe failure and retries", async () => {
  const list = vi
    .spyOn(catalogApi, "books")
    .mockRejectedValueOnce(new ApiError(503, "SERVICE_UNAVAILABLE"))
    .mockResolvedValue({
      items: [],
      page: 1,
      page_size: 20,
      pages: 0,
      total: 0,
    });
  mount(<CatalogList />);
  expect(await screen.findByRole("alert")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: t.retry }));
  expect(await screen.findByText(t.empty)).toBeTruthy();
  expect(list).toHaveBeenCalledTimes(2);
});
it("shows physical availability on details without a Reader return action", async () => {
  vi.spyOn(catalogApi, "book").mockResolvedValue({
    ...book,
    available_copies: 2,
    shelf_locations: ["A-1", "B-2"],
  });
  mount(<BookDetail id={book.id} />);
  expect(await screen.findByText(`${t.available}: 2 / 3`)).toBeTruthy();
  expect(screen.getByText(`${t.shelves}: A-1, B-2`)).toBeTruthy();
  expect(screen.queryByRole("button", { name: /қайтару/i })).toBeNull();
});
it("submits bibliographic fields and disables duplicate save", async () => {
  vi.spyOn(catalogApi, "save").mockImplementation(() => new Promise(() => {}));
  mount(<BookEditor root="/librarian" />);
  fireEvent.change(screen.getByLabelText(t.titleField + " *"), {
    target: { value: "Жаңа кітап" },
  });
  fireEvent.click(screen.getByRole("button", { name: t.save }));
  await waitFor(() =>
    expect(catalogApi.save).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Жаңа кітап",
        language: "kk",
        author_ids: [],
        category_ids: [],
      }),
      undefined,
    ),
  );
  expect(
    screen.getByRole("button", { name: t.loading }).closest("fieldset")
      ?.disabled,
  ).toBe(true);
});
it("requires archive confirmation before issuing the mutation", async () => {
  vi.spyOn(catalogApi, "book").mockResolvedValue(book);
  vi.spyOn(window, "confirm").mockReturnValue(false);
  mount(<BookEditor root="/librarian" id={book.id} />);
  fireEvent.click(await screen.findByRole("button", { name: t.archive }));
  expect(window.confirm).toHaveBeenCalled();
  expect(apiMutation).not.toHaveBeenCalled();
});
