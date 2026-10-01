"use client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analytics as t } from "@/locales/analytics";
import type { Point } from "./api";
const colors = ["#047857", "#2563eb", "#a16207"];
function DataTable({ rows }: { rows: { name: string; count: number }[] }) {
  return (
    <details className="mt-4">
      <summary className="cursor-pointer text-sm text-primary">
        {t.table}
      </summary>
      <div className="max-h-72 overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="p-2 text-left">{t.name}</th>
              <th className="p-2 text-right">{t.count}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                <td className="border-t p-2">{row.name}</td>
                <td className="border-t p-2 text-right">{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
export function TrendChart({
  title,
  series,
}: {
  title: string;
  series: { name: string; points: Point[] }[];
}) {
  const dates = series[0]?.points.map((point) => point.date) ?? [];
  const data = dates.map((date, index) => ({
    date,
    ...Object.fromEntries(
      series.map((line, i) => [`s${i}`, line.points[index]?.count ?? 0]),
    ),
  }));
  const hasData = series.some((line) =>
    line.points.some((point) => point.count > 0),
  );
  return (
    <section
      aria-label={title}
      className="min-w-0 rounded-xl border bg-white p-5"
    >
      <h3 className="mb-4 text-lg font-semibold">{title}</h3>
      {hasData ? (
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <LineChart
              data={data}
              margin={{ top: 10, right: 15, bottom: 30, left: 15 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                minTickGap={30}
                label={{
                  value: t.axisDate,
                  position: "insideBottom",
                  offset: -20,
                }}
              />
              <YAxis
                domain={[0, "auto"]}
                allowDecimals={false}
                label={{ value: t.count, angle: -90, position: "insideLeft" }}
              />
              <Tooltip />
              <Legend verticalAlign="top" />
              {series.map((line, i) => (
                <Line
                  key={line.name}
                  type="linear"
                  dataKey={`s${i}`}
                  name={line.name}
                  stroke={colors[i % colors.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p>{t.empty}</p>
      )}
      <DataTable
        rows={series.flatMap((line) =>
          line.points.map((point) => ({
            name: `${point.date} · ${line.name}`,
            count: point.count,
          })),
        )}
      />
    </section>
  );
}
export function DistributionChart({
  title,
  rows,
}: {
  title: string;
  rows: { name: string; count: number }[];
}) {
  return (
    <section
      aria-label={title}
      className="min-w-0 rounded-xl border bg-white p-5"
    >
      <h3 className="mb-4 text-lg font-semibold">{title}</h3>
      {rows.some((row) => row.count > 0) ? (
        <div className="h-96 w-full">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart
              layout="vertical"
              data={rows}
              margin={{ left: 10, right: 20, bottom: 25, top: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                type="number"
                domain={[0, "auto"]}
                allowDecimals={false}
                label={{
                  value: t.count,
                  position: "insideBottom",
                  offset: -15,
                }}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={125}
                tickFormatter={(value) =>
                  String(value).length > 20
                    ? String(value).slice(0, 19) + "…"
                    : String(value)
                }
              />
              <Tooltip />
              <Bar dataKey="count" name={t.count} fill={colors[0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p>{t.empty}</p>
      )}
      <DataTable rows={rows} />
    </section>
  );
}
