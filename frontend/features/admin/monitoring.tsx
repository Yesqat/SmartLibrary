"use client";
import Link from "next/link";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  CatalogShell,
  Failure,
  Field,
  inputClass,
  Pager,
} from "@/features/catalog/shared";
import { LoanCard } from "@/features/reader/loans";
import { reader as rt } from "@/locales/reader";
import { reservations as rst } from "@/locales/reservations";
import { readerDate } from "@/features/reader/api";
import { admin as t } from "@/locales/admin";
import { adminApi } from "./api";
function useFilters() {
  const search = useSearchParams();
  const [page, setPage] = useState(1),
    [filters, setFilters] = useState<Record<string, string>>({
      user_id: search.get("user_id") ?? "",
    });
  const params = new URLSearchParams({
    page: String(page),
    ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
  });
  const update = (form: HTMLFormElement) => {
    const values = new FormData(form);
    setFilters(Object.fromEntries([...values].map(([k, v]) => [k, String(v)])));
    setPage(1);
  };
  return { page, setPage, params, filters, update };
}
function FilterForm({
  update,
  userId,
  loans,
}: {
  update: (form: HTMLFormElement) => void;
  userId?: string;
  loans: boolean;
}) {
  return (
    <form
      className="mb-6 flex flex-wrap items-end gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        update(e.currentTarget);
      }}
    >
      <Field label={t.monitorSearch}>
        <input className={inputClass} name="q" maxLength={500} />
      </Field>
      <Field label={t.status}>
        <select name="status" className={inputClass}>
          <option value="">{t.all}</option>
          {Object.entries(loans ? rt.states : rst.states).map(
            ([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ),
          )}
        </select>
      </Field>
      <Field label={t.userId}>
        <input
          className={inputClass}
          name="user_id"
          maxLength={36}
          defaultValue={userId}
        />
      </Field>
      {loans && (
        <label>
          <input type="checkbox" name="overdue" value="true" /> {t.overdue}
        </label>
      )}
      <Button>{t.filter}</Button>
    </form>
  );
}
export function AdminBorrowings() {
  const f = useFilters(),
    result = useQuery({
      queryKey: ["borrowings", "admin", f.page, f.filters],
      queryFn: () => adminApi.borrowings(f.params),
      refetchInterval: 30000,
    });
  return (
    <CatalogShell title={t.borrowings}>
      <FilterForm update={f.update} userId={f.filters.user_id} loans />
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {!result.data.total && <p>{t.empty}</p>}
          <ul className="grid gap-5 md:grid-cols-2">
            {result.data.items.map((row) => (
              <li key={row.id}>
                <Link
                  className="mb-2 inline-block text-primary underline"
                  href={`/admin/users/${row.user_id}`}
                >
                  {row.reader_name}
                </Link>
                <LoanCard loan={row} />
              </li>
            ))}
          </ul>
          <Pager page={f.page} pages={result.data.pages} onChange={f.setPage} />
        </>
      )}
    </CatalogShell>
  );
}
export function AdminReservations() {
  const f = useFilters(),
    result = useQuery({
      queryKey: ["reservations", "admin", f.page, f.filters],
      queryFn: () => adminApi.reservations(f.params),
      refetchInterval: 30000,
    });
  return (
    <CatalogShell title={t.reservations}>
      <FilterForm update={f.update} userId={f.filters.user_id} loans={false} />
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
                <h2 className="font-semibold">{row.book_title}</h2>
                <p>
                  {row.reservation_number} · {rst.states[row.status]}
                </p>
                <Link
                  className="text-primary underline"
                  href={`/admin/users/${row.reader_id}`}
                >
                  {row.reader_name}
                </Link>
                <p className="mt-2 text-sm">
                  {rst.created}: {readerDate(row.reserved_at)}
                </p>
                {row.expires_at && (
                  <p className="text-sm">
                    {rst.expires}: {readerDate(row.expires_at)}
                  </p>
                )}
              </li>
            ))}
          </ul>
          <Pager page={f.page} pages={result.data.pages} onChange={f.setPage} />
        </>
      )}
    </CatalogShell>
  );
}
