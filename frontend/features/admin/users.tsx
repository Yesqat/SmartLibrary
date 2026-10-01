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
import { adminApi } from "./api";
export function Users({ librarians = false }: { librarians?: boolean }) {
  const [page, setPage] = useState(1),
    [filter, setFilter] = useState({ q: "", role: "", status: "" });
  const params = new URLSearchParams({
    page: String(page),
    ...Object.fromEntries(Object.entries(filter).filter(([, v]) => v)),
  });
  const result = useQuery({
    queryKey: ["admin-users", librarians, page, filter],
    queryFn: () => adminApi.users(params, librarians),
  });
  return (
    <CatalogShell title={librarians ? t.librarians : t.users}>
      <form
        className="mb-6 flex flex-wrap items-end gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          const data = new FormData(e.currentTarget);
          setFilter({
            q: String(data.get("q") ?? ""),
            role: String(data.get("role") ?? ""),
            status: String(data.get("status") ?? ""),
          });
          setPage(1);
        }}
      >
        <Field label={t.search}>
          <input name="q" className={inputClass} maxLength={500} />
        </Field>
        {!librarians && (
          <Field label={t.role}>
            <select name="role" className={inputClass}>
              <option value="">{t.all}</option>
              {Object.entries(t.roles).map(([key, label]) => (
                <option value={key} key={key}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field label={t.status}>
          <select name="status" className={inputClass}>
            <option value="">{t.all}</option>
            {Object.entries(t.statuses).map(([key, label]) => (
              <option value={key} key={key}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Button>{t.find}</Button>
      </form>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {!result.data.total && <p>{t.empty}</p>}
          <ul className="grid gap-4 md:grid-cols-2">
            {result.data.items.map((row) => (
              <li className="rounded-xl border bg-white p-5" key={row.id}>
                <Link
                  className="text-lg font-semibold text-primary underline"
                  href={`/admin/users/${row.id}`}
                >
                  {row.first_name} {row.last_name}
                </Link>
                <p>{row.email}</p>
                <p>
                  {t.roles[row.role]} · {t.statuses[row.status]}
                </p>
              </li>
            ))}
          </ul>
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
