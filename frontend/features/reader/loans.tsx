"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CatalogShell, Failure, Pager } from "@/features/catalog/shared";
import { reader as t } from "@/locales/reader";
import { readerApi, readerDate, type Loan } from "./api";
export function LoanCard({ loan }: { loan: Loan }) {
  const [clock, setClock] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 30000);
    return () => clearInterval(timer);
  }, []);
  const overdue =
    loan.is_overdue ||
    (["BORROWED", "OVERDUE"].includes(loan.status) &&
      new Date(loan.due_at).getTime() < clock);
  const remaining = Math.max(
    0,
    Math.ceil((new Date(loan.due_at).getTime() - clock) / 86400000),
  );
  const lateDays = Math.max(
    1,
    Math.ceil((clock - new Date(loan.due_at).getTime()) / 86400000),
  );
  return (
    <article className="rounded-xl border bg-white p-5">
      <Link
        className="text-lg font-semibold text-primary underline"
        href={`/books/${loan.book_id}`}
      >
        {loan.book_title}
      </Link>
      <p className="mt-2">{t.states[overdue ? "OVERDUE" : loan.status]}</p>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt>{t.inventory}</dt>
          <dd>{loan.inventory_number}</dd>
        </div>
        <div>
          <dt>{t.borrowed}</dt>
          <dd>{readerDate(loan.borrowed_at)}</dd>
        </div>
        <div>
          <dt>{t.due}</dt>
          <dd>{readerDate(loan.due_at)}</dd>
        </div>
        {loan.returned_at && (
          <div>
            <dt>{t.returned}</dt>
            <dd>{readerDate(loan.returned_at)}</dd>
          </div>
        )}
        {loan.lost_at && (
          <div>
            <dt>{t.lost}</dt>
            <dd>{readerDate(loan.lost_at)}</dd>
          </div>
        )}
      </dl>
      {overdue ? (
        <p className="mt-3 font-semibold text-red-800">
          {t.overdue}
          <span className="block text-sm">Кешіккен күн: {lateDays}</span>
        </p>
      ) : (
        loan.status === "BORROWED" && (
          <p className="mt-3">
            {t.remaining}: {remaining}
          </p>
        )
      )}
    </article>
  );
}
export function MyLoans({ history = false }: { history?: boolean }) {
  const [page, setPage] = useState(1);
  const result = useQuery({
    queryKey: ["borrowings", history, page],
    queryFn: () => readerApi.loans(page, history),
    refetchInterval: 30000,
  });
  return (
    <CatalogShell title={history ? t.history : t.loans}>
      <p className="mb-6">{t.returnInstruction}</p>
      <Link
        href={history ? "/my-books" : "/history"}
        className="text-primary underline"
      >
        {history ? t.loans : t.history}
      </Link>
      <div className="mt-6">
        {result.isPending ? (
          <p role="status">{t.loading}</p>
        ) : result.isError ? (
          <Failure error={result.error} retry={() => void result.refetch()} />
        ) : (
          <>
            {!result.data.total && <p>{t.empty}</p>}
            <ul className="space-y-4">
              {result.data.items.map((loan) => (
                <li key={loan.id}>
                  <LoanCard loan={loan} />
                </li>
              ))}
            </ul>
            <Pager page={page} pages={result.data.pages} onChange={setPage} />
          </>
        )}
      </div>
    </CatalogShell>
  );
}
