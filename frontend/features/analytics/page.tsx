"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { CatalogShell, inputClass } from "@/features/catalog/shared";
import { analytics as t } from "@/locales/analytics";
import type { Dates } from "./api";
import {
  AIPanel,
  CirculationPanel,
  InventoryPanel,
  OverviewPanel,
  ReadersPanel,
  SearchPanel,
} from "./panels";
const panels = {
  overview: OverviewPanel,
  circulation: CirculationPanel,
  inventory: InventoryPanel,
  readers: ReadersPanel,
  search: SearchPanel,
  ai: AIPanel,
};
export function AnalyticsPage({ aiOnly = false }: { aiOnly?: boolean }) {
  const [section, setSection] = useState<keyof typeof panels>(
    aiOnly ? "ai" : "overview",
  );
  const [dates, setDates] = useState<Dates>({});
  const [from, setFrom] = useState(""),
    [to, setTo] = useState("");
  const Panel = panels[section];
  return (
    <CatalogShell title={aiOnly ? t.aiTitle : t.title}>
      <p className="mb-5 text-sm">{t.snapshot}</p>
      <form
        className="mb-7 flex flex-wrap items-end gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          setDates({ date_from: from || undefined, date_to: to || undefined });
        }}
      >
        <label className="grid gap-2 text-sm">
          {t.from}
          <input
            type="date"
            min="1900-01-01"
            max={to || "9998-12-31"}
            value={from}
            onChange={(event) => setFrom(event.target.value)}
            className={inputClass}
          />
        </label>
        <label className="grid gap-2 text-sm">
          {t.to}
          <input
            type="date"
            min={from || "1900-01-01"}
            max="9998-12-31"
            value={to}
            onChange={(event) => setTo(event.target.value)}
            className={inputClass}
          />
        </label>
        <Button type="submit">{t.apply}</Button>
      </form>
      <nav aria-label={t.title} className="mb-7 flex flex-wrap gap-2">
        {(Object.keys(panels) as (keyof typeof panels)[])
          .filter((key) => !aiOnly || ["search", "ai"].includes(key))
          .map((key) => (
            <Button
              key={key}
              variant={section === key ? "default" : "outline"}
              aria-pressed={section === key}
              onClick={() => setSection(key)}
            >
              {t[key]}
            </Button>
          ))}
      </nav>
      <Panel dates={dates} />
    </CatalogShell>
  );
}
