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
import { PredictionReview } from "@/features/categorization/review";
import {
  categorizationApi,
  type PredictionRun,
} from "@/features/categorization/api";
import { categorization as t } from "@/locales/categorization";
const run: PredictionRun = {
  id: "run",
  book_id: "book",
  book_title: "Python",
  model_name: "real-model",
  model_revision: "revision",
  review_status: "PENDING",
  created_at: "2026-01-01T00:00:00Z",
  reviewed_at: null,
  reviewed_by: null,
  threshold: 0.8,
  predictions: [
    {
      id: "p1",
      category_id: "one",
      name: "Programming",
      confidence: 0.9,
      score_kind: "COSINE_SIMILARITY",
      accepted: null,
    },
    {
      id: "p2",
      category_id: "two",
      name: "Science",
      confidence: 0.82,
      score_kind: "COSINE_SIMILARITY",
      accepted: null,
    },
  ],
  selected_categories: [],
};
function mount() {
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      <PredictionReview run={run} />
    </QueryClientProvider>,
  );
}
beforeEach(() => vi.restoreAllMocks());
afterEach(cleanup);
it("does not assign predictions until staff confirms the final selection", async () => {
  const review = vi.spyOn(categorizationApi, "review").mockResolvedValue({
    ...run,
    review_status: "MODIFIED",
    selected_categories: [{ id: "one", name: "Programming" }],
  });
  const confirmation = vi.spyOn(window, "confirm").mockReturnValue(false);
  mount();
  expect(review).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("checkbox", { name: /Science/ }));
  fireEvent.click(screen.getByRole("button", { name: t.save }));
  expect(review).not.toHaveBeenCalled();
  confirmation.mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: t.save }));
  await waitFor(() =>
    expect(review).toHaveBeenCalledExactlyOnceWith("run", ["one"]),
  );
  expect(await screen.findByText(t.success)).toBeInTheDocument();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
});
it("reject-all is explicit and disabling the pending save prevents duplicate submission", async () => {
  const review = vi
    .spyOn(categorizationApi, "review")
    .mockImplementation(() => new Promise(() => {}));
  vi.spyOn(window, "confirm").mockReturnValue(true);
  mount();
  fireEvent.click(screen.getByRole("button", { name: t.reject }));
  expect(
    screen
      .getAllByRole("checkbox")
      .every((checkbox) => !(checkbox as HTMLInputElement).checked),
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: t.save }));
  await waitFor(() => expect(review).toHaveBeenCalledWith("run", []));
  expect(screen.getByRole("button", { name: t.save })).toBeDisabled();
});
