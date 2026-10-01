"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  CatalogShell,
  Failure,
  Field,
  inputClass,
  Pager,
} from "@/features/catalog/shared";
import { readerDate } from "@/features/reader/api";
import { admin as t } from "@/locales/admin";
import { adminApi } from "./api";
export function Audit() {
  const [filters, setFilters] = useState<Record<string, string>>({}),
    [page, setPage] = useState(1);
  const result = useQuery({
    queryKey: ["audit-logs", page, filters],
    queryFn: () => adminApi.audit(page, filters),
  });
  return (
    <CatalogShell title={t.audit}>
      <p className="mb-5">{t.auditHint}</p>
      <form
        className="mb-6 grid items-end gap-4 sm:grid-cols-2 lg:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault();
          setFilters(
            Object.fromEntries(
              [...new FormData(e.currentTarget)].map(([k, v]) => [
                k,
                String(v),
              ]),
            ),
          );
          setPage(1);
        }}
      >
        <Field label={t.from}>
          <input type="date" name="date_from" className={inputClass} />
        </Field>
        <Field label={t.to}>
          <input type="date" name="date_to" className={inputClass} />
        </Field>
        <Field label={t.actor}>
          <input name="actor" className={inputClass} maxLength={36} />
        </Field>
        <Field label={t.action}>
          <input name="action" className={inputClass} maxLength={100} />
        </Field>
        <Field label={t.entity}>
          <input name="entity_type" className={inputClass} maxLength={100} />
        </Field>
        <Button>{t.filter}</Button>
      </form>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {!result.data.total && <p>{t.empty}</p>}
          <ul className="space-y-4">
            {result.data.items.map((row) => (
              <li className="rounded-xl border bg-white p-5" key={row.id}>
                <p className="font-semibold">
                  {row.action} · {readerDate(row.created_at)}
                </p>
                <p>{row.actor_name ?? "—"}</p>
                <p className="text-sm break-all">
                  {row.entity_type} · {row.entity_id ?? "—"}
                </p>
                <p className="mt-2 text-sm">{row.details.reason ?? ""}</p>
              </li>
            ))}
          </ul>
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
