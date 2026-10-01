import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { SearchCatalog } from "@/features/catalog/search-catalog";
import { SearchInput } from "@/features/catalog/search-input";
import { SearchFilters } from "@/features/catalog/search-filters";
import { searchApi } from "@/features/catalog/search-api";
import { apiRequest, clearSession } from "@/services/api-client";
import { searchText as s } from "@/locales/search";
import { catalog as t } from "@/locales/catalog";
const navigation = vi.hoisted(() => ({ params: "q=Абай", push: vi.fn() }));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(navigation.params),
  useRouter: () => ({ push: navigation.push }),
}));
vi.mock("@/services/api-client", async (original) => ({
  ...(await original<typeof import("@/services/api-client")>()),
  apiRequest: vi.fn(),
}));
function mount(ui: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {ui}
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
  clearSession();
  navigation.params = "q=Абай";
});
afterEach(cleanup);

it("sends the URL query to the backend and shows the real result count", async () => {
  const search = vi.spyOn(searchApi, "search").mockResolvedValue({
    items: [],
    page: 1,
    page_size: 20,
    total: 0,
    pages: 0,
    search_event_id: null,
    indexing_pending: false,
  });
  mount(<SearchCatalog />);
  expect(await screen.findByText(`${s.results}: 0`)).toBeTruthy();
  expect(search.mock.calls[0][0].get("q")).toBe("Абай");
  fireEvent.change(screen.getByRole("combobox", { name: s.sort }), {
    target: { value: "year_desc" },
  });
  expect(navigation.push).toHaveBeenCalledWith(
    expect.stringContaining("sort=year_desc"),
  );
});
it("submits a new query with prior filters and resets page", async () => {
  navigation.params = "q=old&page=3&available=true";
  vi.spyOn(searchApi, "search").mockResolvedValue({
    items: [],
    page: 3,
    page_size: 20,
    total: 0,
    pages: 0,
    search_event_id: null,
    indexing_pending: false,
  });
  mount(<SearchCatalog />);
  fireEvent.change(screen.getByRole("searchbox", { name: s.placeholder }), {
    target: { value: "Clean Code" },
  });
  fireEvent.click(screen.getByRole("button", { name: t.find }));
  const params = new URLSearchParams(
    navigation.push.mock.calls[0][0].split("?")[1],
  );
  expect(params.get("q")).toBe("Clean Code");
  expect(params.get("available")).toBe("true");
  expect(params.has("page")).toBe(false);
});

it("keeps filters while selecting semantic search and shows pending indexing", async () => {
  navigation.params = "q=ғарыш&language=en&page=3";
  vi.spyOn(searchApi, "search").mockResolvedValue({
    items: [],
    page: 1,
    page_size: 20,
    total: 0,
    pages: 0,
    search_event_id: null,
    indexing_pending: true,
  });
  mount(<SearchCatalog />);
  expect(await screen.findByText(s.indexing)).toBeTruthy();
  fireEvent.change(screen.getByRole("combobox", { name: s.mode }), {
    target: { value: "semantic" },
  });
  const params = new URLSearchParams(
    navigation.push.mock.calls[0][0].split("?")[1],
  );
  expect(params.get("mode")).toBe("semantic");
  expect(params.get("language")).toBe("en");
  expect(params.has("page")).toBe(false);
});
it("loads backend suggestions and links authors to their search context", async () => {
  const autocomplete = vi.spyOn(searchApi, "autocomplete").mockResolvedValue({
    items: [{ id: "author-id", kind: "author", label: "Абай Құнанбайұлы" }],
  });
  function Input() {
    return <SearchInput value="Аба" onChange={() => {}} />;
  }
  mount(<Input />);
  fireEvent.focus(screen.getByRole("searchbox"));
  const link = await screen.findByRole("link", { name: /Абай Құнанбайұлы/ });
  expect(
    new URLSearchParams(link.getAttribute("href")!.split("?")[1]).get("q"),
  ).toBe("Абай Құнанбайұлы");
  expect(autocomplete).toHaveBeenCalledWith("Аба", expect.any(AbortSignal));
});

it("debounces consecutive input changes into one backend request", async () => {
  const autocomplete = vi
    .spyOn(searchApi, "autocomplete")
    .mockResolvedValue({ items: [] });
  function Input() {
    const [value, setValue] = useState("");
    return <SearchInput value={value} onChange={setValue} />;
  }
  mount(<Input />);
  const input = screen.getByRole("searchbox");
  fireEvent.focus(input);
  fireEvent.change(input, { target: { value: "Cle" } });
  fireEvent.change(input, { target: { value: "Clean" } });
  expect(autocomplete).not.toHaveBeenCalled();
  await waitFor(() => expect(autocomplete).toHaveBeenCalledTimes(1));
  expect(autocomplete).toHaveBeenCalledWith("Clean", expect.any(AbortSignal));
});
it("restores a selected reference from the backend and combines filter values", async () => {
  vi.mocked(apiRequest).mockResolvedValue({
    id: "category-id",
    name: "Ғылым",
    description: null,
    archived_at: null,
  });
  const apply = vi.fn();
  mount(
    <SearchFilters
      params={new URLSearchParams("q=book&category=category-id&page=2")}
      onApply={apply}
    />,
  );
  expect(
    await screen.findByRole("button", { name: `${t.cancel}: Ғылым` }),
  ).toBeTruthy();
  fireEvent.change(screen.getByRole("combobox", { name: s.availability }), {
    target: { value: "true" },
  });
  fireEvent.change(screen.getByRole("spinbutton", { name: s.yearFrom }), {
    target: { value: "2000" },
  });
  fireEvent.click(screen.getByRole("checkbox", { name: s.languages.kk }));
  fireEvent.click(screen.getByRole("button", { name: s.apply }));
  await waitFor(() => expect(apply).toHaveBeenCalled());
  const params = apply.mock.calls[0][0] as URLSearchParams;
  expect(params.get("category")).toBe("category-id");
  expect(params.get("available")).toBe("true");
  expect(params.get("year_from")).toBe("2000");
  expect(params.getAll("language")).toEqual(["kk"]);
  expect(params.has("page")).toBe(false);
});
