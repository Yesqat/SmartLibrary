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
import { librarian as t } from "@/locales/librarian";
import { reservations as rt } from "@/locales/reservations";
import { readerDate } from "@/features/reader/api";
import { librarianApi } from "./api";
export function StaffReservations({ readerId }: { readerId?: string }) {
  const [page, setPage] = useState(1),
    [q, setQ] = useState(""),
    [status, setStatus] = useState("");
  const result = useQuery({
    queryKey: ["reservations", "staff", readerId, page, q, status],
    queryFn: () => librarianApi.reservations(page, q, status, readerId),
    refetchInterval: 30000,
  });
  return (
    <section>
      <form
        className="mb-5 flex flex-wrap items-end gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          setQ(String(new FormData(e.currentTarget).get("q")));
          setPage(1);
        }}
      >
        <Field label={t.reservationSearch}>
          <input className={inputClass} name="q" maxLength={500} />
        </Field>
        <Field label={t.status}>
          <select
            className={inputClass}
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">{t.all}</option>
            {Object.entries(rt.states).map(([key, value]) => (
              <option key={key} value={key}>
                {value}
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
              <li key={row.id} className="rounded-xl border bg-white p-5">
                <h3 className="font-semibold">{row.book_title}</h3>
                <p>
                  {row.reservation_number} · {rt.states[row.status]}
                </p>
                <Link
                  className="text-primary underline"
                  href={`/librarian/readers/${row.reader_id}`}
                >
                  {row.reader_name}
                </Link>
                <p className="mt-2 text-sm">
                  {rt.created}: {readerDate(row.reserved_at)}
                </p>
                {row.expires_at && (
                  <p className="text-sm">
                    {rt.expires}: {readerDate(row.expires_at)}
                  </p>
                )}
                {row.queue_position !== null && (
                  <p>
                    {rt.position}: {row.queue_position}
                  </p>
                )}
                {row.qr_available && (
                  <Link
                    className="mt-3 inline-block text-primary underline"
                    href="/librarian/qr"
                  >
                    {t.manual}
                  </Link>
                )}
              </li>
            ))}
          </ul>
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </section>
  );
}
export function ReservationPanel() {
  return (
    <CatalogShell title={t.reservations}>
      <StaffReservations />
    </CatalogShell>
  );
}
