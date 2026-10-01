"use client";
import Link from "next/link";
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
import { admin as t } from "@/locales/admin";
import { catalog as ct } from "@/locales/catalog";
import { adminApi } from "./api";
export function Inventory() {
  const [filters, setFilters] = useState({
      q: "",
      status: "",
      include_archived: "false",
    }),
    [page, setPage] = useState(1);
  const params = new URLSearchParams({
    ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
    page: String(page),
  });
  const result = useQuery({
    queryKey: ["catalog", "inventory", page, filters],
    queryFn: () => adminApi.inventory(params),
  });
  return (
    <CatalogShell title={t.inventory}>
      <form
        className="mb-6 flex flex-wrap items-end gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          const form = new FormData(e.currentTarget);
          setFilters({
            q: String(form.get("q")),
            status: String(form.get("status")),
            include_archived: String(form.has("archived")),
          });
          setPage(1);
        }}
      >
        <Field label={t.inventorySearch}>
          <input className={inputClass} name="q" maxLength={500} />
        </Field>
        <Field label={t.status}>
          <select name="status" className={inputClass}>
            <option value="">{t.all}</option>
            {Object.entries(ct.statuses).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <label>
          <input type="checkbox" name="archived" /> {t.archived}
        </label>
        <Button>{t.find}</Button>
      </form>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {!result.data.total && <p>{t.empty}</p>}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr>
                  {[
                    ct.title,
                    ct.inventory,
                    ct.shelf,
                    ct.status,
                    ct.condition,
                  ].map((label) => (
                    <th className="border-b p-3" key={label}>
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.data.items.map((row) => (
                  <tr key={row.id}>
                    <td className="border-b p-3">
                      <Link
                        className="text-primary underline"
                        href={`/admin/books/${row.book_id}/copies`}
                      >
                        {row.book_title}
                      </Link>
                      {(row.archived_at || row.book_archived) && (
                        <p>{ct.archived}</p>
                      )}
                    </td>
                    <td className="border-b p-3">{row.inventory_number}</td>
                    <td className="border-b p-3">
                      {row.shelf_location ?? "—"}
                    </td>
                    <td className="border-b p-3">{ct.statuses[row.status]}</td>
                    <td className="border-b p-3">
                      {ct.conditions[row.condition]}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
