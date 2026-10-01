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
import { LoanCard } from "@/features/reader/loans";
import { librarian as t } from "@/locales/librarian";
import { librarianApi } from "./api";
export function Overdue() {
  const [filters, setFilters] = useState({ q: "", days: 0, order: "oldest" }),
    [page, setPage] = useState(1);
  const result = useQuery({
    queryKey: ["borrowings", "overdue", page, filters],
    queryFn: () =>
      librarianApi.overdue(page, filters.q, filters.days, filters.order),
    refetchInterval: 30000,
  });
  return (
    <CatalogShell title={t.overdue}>
      <form
        className="mb-6 flex flex-wrap items-end gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          const form = new FormData(e.currentTarget);
          setFilters({
            q: String(form.get("q")),
            days: Number(form.get("days")),
            order: String(form.get("order")),
          });
          setPage(1);
        }}
      >
        <Field label={t.bookSearch}>
          <input className={inputClass} name="q" maxLength={500} />
        </Field>
        <Field label={t.minimumDays}>
          <input
            className={inputClass}
            name="days"
            type="number"
            min={0}
            max={36500}
            defaultValue={0}
          />
        </Field>
        <Field label={t.sort}>
          <select name="order" className={inputClass}>
            <option value="oldest">{t.oldest}</option>
            <option value="newest">{t.newest}</option>
            <option value="reader">{t.byReader}</option>
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
          <ul className="grid gap-5 md:grid-cols-2">
            {result.data.items.map((loan) => (
              <li key={loan.id}>
                <Link
                  className="mb-2 inline-block text-primary underline"
                  href={`/librarian/readers/${loan.user_id}`}
                >
                  {loan.reader_name}
                </Link>
                <LoanCard loan={loan} />
              </li>
            ))}
          </ul>
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
