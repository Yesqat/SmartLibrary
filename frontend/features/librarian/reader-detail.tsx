"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { CatalogShell, Failure, Pager } from "@/features/catalog/shared";
import { LoanCard } from "@/features/reader/loans";
import { readerDate } from "@/features/reader/api";
import { librarian as t } from "@/locales/librarian";
import { librarianApi, type ReaderDetail as Detail } from "./api";
import { StaffReservations } from "./reservations";
export function ReaderEligibility({ data }: { data: Detail }) {
  return (
    <div className="my-5 rounded-xl border p-5">
      <p>
        {t.status}: {t.states[data.reader.status]}
      </p>
      <p>
        {t.limit}: {data.active_borrowings} / {data.borrowing_limit}
      </p>
      <p>
        {t.overdue}: {data.overdue_borrowings}
      </p>
      <p>
        {t.duePreview}: {readerDate(data.prospective_due_at)}
      </p>
      {!data.can_borrow && (
        <p role="alert" className="mt-3 font-semibold text-red-800">
          {t.blocked}
        </p>
      )}
    </div>
  );
}
export function ReaderDetails({ id }: { id: string }) {
  const [active, setActive] = useState(true),
    [page, setPage] = useState(1);
  const result = useQuery({
    queryKey: ["readers", id],
    queryFn: () => librarianApi.reader(id),
    refetchInterval: 30000,
  });
  const loans = useQuery({
    queryKey: ["borrowings", "reader", id, page, active],
    queryFn: () => librarianApi.loans(id, page, active),
    enabled: !!result.data,
  });
  return (
    <CatalogShell title={t.reader}>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          <h2 className="text-xl font-semibold">
            {result.data.reader.first_name} {result.data.reader.last_name}
          </h2>
          <p>{result.data.reader.email}</p>
          <p>
            {t.phone}: {result.data.phone ?? "—"}
          </p>
          <ReaderEligibility data={result.data} />
          <div className="my-5 flex gap-3">
            {[true, false].map((value) => (
              <Button
                key={String(value)}
                variant={active === value ? "default" : "outline"}
                aria-pressed={active === value}
                onClick={() => {
                  setActive(value);
                  setPage(1);
                }}
              >
                {value ? t.active : t.history}
              </Button>
            ))}
          </div>
          {loans.isPending ? (
            <p role="status">{t.loading}</p>
          ) : loans.isError ? (
            <Failure error={loans.error} retry={() => void loans.refetch()} />
          ) : (
            <>
              {!loans.data.total && <p>{t.empty}</p>}
              <div className="grid gap-4 md:grid-cols-2">
                {loans.data.items.map((loan) => (
                  <LoanCard key={loan.id} loan={loan} />
                ))}
              </div>
              <Pager page={page} pages={loans.data.pages} onChange={setPage} />
            </>
          )}
          <h2 className="my-6 text-xl font-semibold">{t.reservations}</h2>
          <StaffReservations readerId={id} />
        </>
      )}
    </CatalogShell>
  );
}
