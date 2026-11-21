"use client";
import { useQuery } from "@tanstack/react-query";
import { Failure } from "@/features/catalog/shared";
import { readerDate } from "@/features/reader/api";
import { analytics as t } from "@/locales/analytics";
import {
  analyticsApi,
  type AI,
  type Circulation,
  type Dates,
  type Inventory,
  type Period,
  type Readers,
} from "./api";
import { DistributionChart, TrendChart } from "./charts";
import styles from "@/features/catalog/workspace.module.css";
type Metrics = Record<string, unknown>;
function Cards({
  data,
  keys,
}: {
  data: Metrics;
  keys: (keyof typeof t.metrics)[];
}) {
  return (
    <dl className={styles.metrics}>
      {keys.map((key) => (
        <div key={key}>
          <dt>{t.metrics[key]}</dt>
          <dd className="mt-2 text-2xl font-semibold">
            {typeof data[key] === "number"
              ? new Intl.NumberFormat("kk-KZ", {
                  maximumFractionDigits: 2,
                }).format(data[key] as number)
              : t.unavailable}
          </dd>
        </div>
      ))}
    </dl>
  );
}
function Stamp({ period }: { period: Period }) {
  return (
    <p className="text-sm text-muted-foreground">
      {t.period}: {period.date_from} — {period.date_to}. {t.timezone}:{" "}
      {period.timezone}. {t.bucket}: {t[period.bucket]}. {t.generated}:{" "}
      {readerDate(period.generated_at)}
    </p>
  );
}
const stateRows = (rows: { key: string; count: number }[]) =>
  rows.map((row) => ({
    name: t.states[row.key as keyof typeof t.states] ?? row.key,
    count: row.count,
  }));
function CirculationView({
  data,
  compact = false,
}: {
  data: Circulation;
  compact?: boolean;
}) {
  return (
    <div className="space-y-5">
      {!compact && (
        <>
          <Cards
            data={data}
            keys={[
              "active_borrowings",
              "overdue_borrowings",
              "active_reservations",
              "waiting_reservations",
              "ready_reservations",
              "issued",
              "returned",
              "lost",
              "reservations_created",
              "reservations_completed",
              "reservations_cancelled",
              "reservations_expired",
              "reservation_completion_rate",
            ]}
          />
          <p className="text-sm">{t.rateDefinition}</p>
        </>
      )}
      <TrendChart
        title={t.charts.loans}
        series={[
          { name: t.metrics.issued, points: data.borrowing_trend },
          { name: t.metrics.returned, points: data.return_trend },
        ]}
      />
      {!compact && (
        <>
          <TrendChart
            title={t.charts.reservations}
            series={[
              {
                name: t.metrics.reservations_created,
                points: data.reservation_trend,
              },
            ]}
          />
          <DistributionChart
            title={t.charts.cohort}
            rows={stateRows(data.reservation_cohort_status)}
          />
        </>
      )}
      <div className="grid gap-5 lg:grid-cols-2">
        <DistributionChart
          title={t.charts.popularBooks}
          rows={data.popular_books.map((row) => ({
            name: row.label,
            count: row.count,
          }))}
        />
        <DistributionChart
          title={t.charts.popularCategories}
          rows={data.popular_categories.map((row) => ({
            name: row.label,
            count: row.count,
          }))}
        />
      </div>
      <p className="text-sm">{t.categoryDefinition}</p>
    </div>
  );
}
function InventoryView({
  data,
  compact = false,
}: {
  data: Inventory;
  compact?: boolean;
}) {
  return (
    <div className="space-y-5">
      {!compact && (
        <Cards
          data={data}
          keys={[
            "book_titles",
            "physical_copies",
            "added_titles",
            "added_copies",
          ]}
        />
      )}
      <DistributionChart
        title={t.charts.inventory}
        rows={stateRows(data.status)}
      />
      {!compact && (
        <TrendChart
          title={t.charts.additions}
          series={[{ name: t.metrics.added_copies, points: data.additions }]}
        />
      )}
    </div>
  );
}
function ReadersView({
  data,
  compact = false,
}: {
  data: Readers;
  compact?: boolean;
}) {
  return (
    <div className="space-y-5">
      {!compact && (
        <>
          <Cards
            data={data}
            keys={[
              "total_readers",
              "active_reader_accounts",
              "active_readers",
              "new_readers",
            ]}
          />
          <p className="text-sm">{t.activeDefinition}</p>
        </>
      )}
      <TrendChart
        title={t.charts.registrations}
        series={[{ name: t.metrics.new_readers, points: data.registrations }]}
      />
    </div>
  );
}
function AIView({ data }: { data: AI }) {
  return (
    <div className="space-y-5">
      <Cards
        data={data}
        keys={[
          "prediction_runs",
          "predictions",
          "reviewed_predictions",
          "accepted_predictions",
          "prediction_acceptance_rate",
          "assistant_questions",
          "assistant_successes",
          "assistant_failures",
          "assistant_conversations",
          "assistant_readers",
          "assistant_average_latency_ms",
          "input_tokens",
          "output_tokens",
          "responses_without_usage",
        ]}
      />
      <p className="text-sm">
        {t.reviewDefinition} {t.tokensNote}
      </p>
      <div className="grid gap-5 lg:grid-cols-2">
        <DistributionChart
          title={t.charts.reviews}
          rows={stateRows(data.review_outcomes)}
        />
        <TrendChart
          title={t.charts.assistant}
          series={[
            {
              name: t.metrics.assistant_questions,
              points: data.assistant_trend,
            },
          ]}
        />
      </div>
      <section className="overflow-auto rounded-xl border bg-white p-5">
        <h3 className="mb-3 text-lg font-semibold">{t.recommendations}</h3>
        <p className="mb-4 text-sm">{t.ctrDefinition}</p>
        <table className="w-full text-sm">
          <thead>
            <tr>
              {[t.name, t.impressions, t.clicks, t.ctr].map((label) => (
                <th key={label} className="p-2 text-left">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.recommendations.map((row) => (
              <tr key={row.kind}>
                <td className="border-t p-2">
                  {t.states[row.kind as keyof typeof t.states]}
                </td>
                <td className="border-t p-2">{row.impressions}</td>
                <td className="border-t p-2">{row.clicks}</td>
                <td className="border-t p-2">
                  {row.ctr === null ? t.unavailable : row.ctr.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
export function OverviewPanel({
  dates = {},
  chartsOnly = false,
}: {
  dates?: Dates;
  chartsOnly?: boolean;
}) {
  const q = useQuery({
    queryKey: ["analytics", "overview", dates],
    queryFn: () => analyticsApi.overview(dates),
    refetchInterval: 60000,
  });
  if (q.isPending) return <p role="status">{t.loading}</p>;
  if (q.isError)
    return <Failure error={q.error} retry={() => void q.refetch()} />;
  return (
    <div className="space-y-5">
      <Stamp period={q.data.period} />
      {!chartsOnly && (
        <>
          <Cards
            data={{
              ...q.data.inventory,
              ...q.data.circulation,
              ...q.data.readers,
            }}
            keys={[
              "book_titles",
              "physical_copies",
              "total_readers",
              "active_readers",
              "active_borrowings",
              "overdue_borrowings",
              "active_reservations",
              "issued",
              "returned",
            ]}
          />
          <p className="text-sm">{t.activeDefinition}</p>
        </>
      )}
      <CirculationView data={q.data.circulation} compact />
      <div className="grid gap-5 lg:grid-cols-2">
        <InventoryView data={q.data.inventory} compact />
        <ReadersView data={q.data.readers} compact />
      </div>
    </div>
  );
}
export function CirculationPanel({ dates }: { dates: Dates }) {
  const q = useQuery({
    queryKey: ["analytics", "circulation", dates],
    queryFn: () => analyticsApi.circulation(dates),
  });
  return q.isPending ? (
    <p role="status">{t.loading}</p>
  ) : q.isError ? (
    <Failure error={q.error} retry={() => void q.refetch()} />
  ) : (
    <div className="space-y-5">
      <Stamp period={q.data.period} />
      <CirculationView data={q.data} />
    </div>
  );
}
export function InventoryPanel({ dates }: { dates: Dates }) {
  const q = useQuery({
    queryKey: ["analytics", "inventory", dates],
    queryFn: () => analyticsApi.inventory(dates),
  });
  return q.isPending ? (
    <p role="status">{t.loading}</p>
  ) : q.isError ? (
    <Failure error={q.error} retry={() => void q.refetch()} />
  ) : (
    <div className="space-y-5">
      <Stamp period={q.data.period} />
      <InventoryView data={q.data} />
    </div>
  );
}
export function ReadersPanel({ dates }: { dates: Dates }) {
  const q = useQuery({
    queryKey: ["analytics", "readers", dates],
    queryFn: () => analyticsApi.readers(dates),
  });
  return q.isPending ? (
    <p role="status">{t.loading}</p>
  ) : q.isError ? (
    <Failure error={q.error} retry={() => void q.refetch()} />
  ) : (
    <div className="space-y-5">
      <Stamp period={q.data.period} />
      <ReadersView data={q.data} />
    </div>
  );
}
export function SearchPanel({ dates }: { dates: Dates }) {
  const q = useQuery({
    queryKey: ["analytics", "search", dates],
    queryFn: () => analyticsApi.search(dates),
  });
  return q.isPending ? (
    <p role="status">{t.loading}</p>
  ) : q.isError ? (
    <Failure error={q.error} retry={() => void q.refetch()} />
  ) : (
    <div className="space-y-5">
      <Stamp period={q.data.period} />
      <Cards
        data={q.data}
        keys={["total_searches", "zero_result_searches", "zero_result_rate"]}
      />
      <TrendChart
        title={t.charts.search}
        series={[{ name: t.metrics.total_searches, points: q.data.trend }]}
      />
      <DistributionChart
        title={t.charts.modes}
        rows={stateRows(q.data.modes)}
      />
      <section className="rounded-xl border bg-white p-5">
        <h3 className="mb-3 text-lg font-semibold">{t.query}</h3>
        {q.data.zero_result_queries.length ? (
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left">{t.query}</th>
                <th>{t.count}</th>
              </tr>
            </thead>
            <tbody>
              {q.data.zero_result_queries.map((row) => (
                <tr key={row.query}>
                  <td className="break-words border-t p-2">{row.query}</td>
                  <td className="border-t p-2 text-center">{row.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>{t.empty}</p>
        )}
      </section>
    </div>
  );
}
export function AIPanel({ dates }: { dates: Dates }) {
  const q = useQuery({
    queryKey: ["analytics", "ai", dates],
    queryFn: () => analyticsApi.ai(dates),
  });
  return q.isPending ? (
    <p role="status">{t.loading}</p>
  ) : q.isError ? (
    <Failure error={q.error} retry={() => void q.refetch()} />
  ) : (
    <div className="space-y-5">
      <Stamp period={q.data.period} />
      <AIView data={q.data} />
    </div>
  );
}
