import "@testing-library/jest-dom/vitest";
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
import {
  RecommendationCard,
  RecommendationSection,
} from "@/features/recommendations/section";
import {
  recommendationApi,
  type RecommendationItem,
} from "@/features/recommendations/api";
import { recommendations as t } from "@/locales/recommendations";
vi.mock("@/features/auth/auth-provider", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "reader", role: "READER" },
  }),
}));
const item: RecommendationItem = {
  reason: "history",
  book: {
    id: "book",
    title: "Python",
    language: "en",
    isbn: null,
    description: null,
    cover_url: null,
    publication_year: null,
    page_count: null,
    publisher: null,
    authors: [],
    categories: [],
    archived_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    available_copies: 0,
    total_copies: 1,
    shelf_locations: [],
  },
};
let visibility: (entries: Partial<IntersectionObserverEntry>[]) => void;
beforeEach(() => {
  vi.restoreAllMocks();
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(callback: typeof visibility) {
        visibility = callback;
      }
      observe() {}
      disconnect() {}
    },
  );
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
it("counts a visible rendered card once after dwell and attributes its click", async () => {
  vi.useFakeTimers();
  const record = vi
    .spyOn(recommendationApi, "impression")
    .mockResolvedValue({ id: "impression" });
  const click = vi
    .spyOn(recommendationApi, "click")
    .mockResolvedValue(undefined);
  render(<RecommendationCard item={item} receipt="signed-offer" />);
  expect(record).not.toHaveBeenCalled();
  act(() => visibility([{ isIntersecting: true, intersectionRatio: 0.6 }]));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(999);
  });
  expect(record).not.toHaveBeenCalled();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1);
  });
  expect(record).toHaveBeenCalledExactlyOnceWith("signed-offer", "book");
  fireEvent.click(screen.getByRole("link", { name: "Python" }));
  await act(async () => {
    await Promise.resolve();
  });
  expect(click).toHaveBeenCalledWith("impression");
  expect(record).toHaveBeenCalledTimes(1);
  expect(screen.getByText("Қолжетімді: 0 / 1")).toBeInTheDocument();
});
it("does not record hidden or offscreen cards", async () => {
  vi.useFakeTimers();
  const record = vi.spyOn(recommendationApi, "impression");
  render(<RecommendationCard item={item} receipt="signed-offer" />);
  act(() => visibility([{ isIntersecting: true, intersectionRatio: 0.2 }]));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000);
  });
  expect(record).not.toHaveBeenCalled();
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
  act(() => visibility([{ isIntersecting: true, intersectionRatio: 1 }]));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000);
  });
  expect(record).not.toHaveBeenCalled();
});
it("handles missing embeddings and a small catalog without fabricated cards", async () => {
  vi.spyOn(recommendationApi, "list").mockResolvedValue({
    items: [],
    recommendation_type: "SIMILAR_BOOK",
    content_available: false,
    indexing_pending: true,
    receipt: null,
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <RecommendationSection kind="similar" bookId="book" />
    </QueryClientProvider>,
  );
  await waitFor(() => expect(screen.getByText(t.pending)).toBeInTheDocument());
  expect(screen.getByText(t.empty)).toBeInTheDocument();
  expect(screen.queryByRole("article")).not.toBeInTheDocument();
});
