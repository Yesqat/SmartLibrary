"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CatalogShell,
  Failure,
  Field,
  Pager,
  inputClass,
} from "@/features/catalog/shared";
import { reservations as t } from "@/locales/reservations";
import { reservationApi } from "./api";
import { Button } from "@/components/ui/button";
import { reader as rt } from "@/locales/reader";

export function ReservationList() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [active, setActive] = useState(true);
  const result = useQuery({
    queryKey: ["reservations", "list", page, status, active],
    queryFn: () => reservationApi.list(page, status, active),
    refetchInterval: 30_000,
  });
  return (
    <CatalogShell title={t.title}>
      <div className="mb-6 flex gap-3" aria-label={t.title}>
        {[true, false].map((value) => (
          <Button
            key={String(value)}
            variant={active === value ? "default" : "outline"}
            aria-pressed={active === value}
            onClick={() => {
              setActive(value);
              setStatus("");
              setPage(1);
            }}
          >
            {value ? rt.active : rt.history}
          </Button>
        ))}
      </div>
      <div className="mb-6 max-w-xs">
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
            {Object.entries(t.states)
              .filter(
                ([value]) => active === ["READY", "WAITING"].includes(value),
              )
              .map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
          </select>
        </Field>
      </div>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {result.data.items.length === 0 ? (
            <p>{t.empty}</p>
          ) : (
            <ul className="space-y-4">
              {result.data.items.map((row) => (
                <li className="rounded-xl border bg-white p-5" key={row.id}>
                  <Link
                    className="text-lg font-semibold text-primary underline"
                    href={`/reservations/${row.id}`}
                  >
                    {row.book_title}
                  </Link>
                  <p className="mt-2">
                    {row.reservation_number} · {t.states[row.status]}
                  </p>
                  <p className="mt-2 text-sm">
                    {t.created}:{" "}
                    {new Date(row.reserved_at).toLocaleString("kk-KZ")}
                  </p>
                  {row.qr_available && (
                    <Link
                      className="mt-3 inline-block text-primary underline"
                      href={`/reservations/${row.id}`}
                    >
                      {t.showQR}
                    </Link>
                  )}
                  {row.queue_position !== null && (
                    <p className="mt-2 text-sm">
                      {t.position}: {row.queue_position}
                    </p>
                  )}
                  {row.expires_at && row.status === "READY" && (
                    <p className="mt-2 text-sm">
                      {t.expires}:{" "}
                      {new Date(row.expires_at).toLocaleString("kk-KZ")}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
