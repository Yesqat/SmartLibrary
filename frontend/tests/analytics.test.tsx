import "@testing-library/jest-dom/vitest";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SearchPanel } from "@/features/analytics/panels";
import { TrendChart } from "@/features/analytics/charts";
import { analyticsApi } from "@/features/analytics/api";
import { analytics as t } from "@/locales/analytics";
import { ApiError } from "@/services/api-client";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
function mount(ui: React.ReactNode) {
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {ui}
    </QueryClientProvider>,
  );
}
it("zero buckets stay accessible without inventing chart activity", () => {
  render(
    <TrendChart
      title="Тіркелу"
      series={[
        {
          name: "Оқырман",
          points: [
            { date: "2025-01-01", count: 0 },
            { date: "2025-01-02", count: 0 },
          ],
        },
      ]}
    />,
  );
  expect(screen.getByText(t.empty)).toBeVisible();
  fireEvent.click(screen.getByText(t.table));
  expect(screen.getByText("2025-01-02 · Оқырман")).toBeVisible();
  expect(screen.getAllByRole("cell").map((c) => c.textContent)).toEqual([
    "2025-01-01 · Оқырман",
    "0",
    "2025-01-02 · Оқырман",
    "0",
  ]);
});
it("search failure offers retry without replacing missing data with zero", async () => {
  vi.spyOn(analyticsApi, "search").mockRejectedValue(
    new ApiError(503, "SERVICE_UNAVAILABLE"),
  );
  mount(<SearchPanel dates={{ date_from: "2025-01-01" }} />);
  expect(await screen.findByRole("alert")).toBeVisible();
  expect(screen.queryByText(t.metrics.total_searches)).toBeNull();
  expect(screen.getByRole("button")).toBeEnabled();
});
it("empty search denominator stays undefined and selected dates reach the API", async () => {
  vi.spyOn(analyticsApi, "search").mockResolvedValue({
    period: {
      date_from: "2080-01-01",
      date_to: "2080-01-01",
      timezone: "Asia/Qyzylorda",
      bucket: "day",
      generated_at: "2080-01-02T00:00:00Z",
    },
    total_searches: 0,
    zero_result_searches: 0,
    zero_result_rate: null,
    modes: [],
    trend: [{ date: "2080-01-01", count: 0 }],
    zero_result_queries: [],
  });
  mount(
    <SearchPanel dates={{ date_from: "2080-01-01", date_to: "2080-01-01" }} />,
  );
  expect(await screen.findByText(t.unavailable)).toBeVisible();
  expect(analyticsApi.search).toHaveBeenCalledWith({
    date_from: "2080-01-01",
    date_to: "2080-01-01",
  });
});
