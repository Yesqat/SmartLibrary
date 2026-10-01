"use client";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { CatalogShell, Failure } from "@/features/catalog/shared";
import { reservations as t } from "@/locales/reservations";
import { reservationApi, type Reservation } from "./api";

function PrivateQR({ row }: { row: Reservation }) {
  const [shown, setShown] = useState(false);
  const [expired, setExpired] = useState(
    () => !row.expires_at || Date.parse(row.expires_at) <= Date.now(),
  );
  useEffect(() => {
    const deadline = row.expires_at ? Date.parse(row.expires_at) : 0;
    const timer = window.setTimeout(
      () => setExpired(true),
      Math.min(Math.max(0, deadline - Date.now()), 2_147_483_647),
    );
    return () => window.clearTimeout(timer);
  }, [row.expires_at]);
  const qr = useQuery({
    queryKey: ["reservation-credential", row.id],
    queryFn: () => reservationApi.qr(row.id),
    enabled: shown && row.qr_available && !expired,
    gcTime: 0,
    staleTime: 0,
    retry: false,
    refetchInterval: shown ? 30_000 : false,
  });
  if (!row.qr_available || expired)
    return row.status === "READY" ? <p role="status">{t.expired}</p> : null;
  return (
    <section className="mt-6 rounded-xl border bg-white p-6">
      <p>{t.pickup}</p>
      <p className="mt-2 text-sm text-muted-foreground">{t.qrPrivate}</p>
      <Button
        className="mt-5"
        variant="outline"
        onClick={() => setShown(!shown)}
      >
        {shown ? t.hideQR : t.showQR}
      </Button>
      {shown && (
        <div className="mt-5">
          {qr.isError ? (
            <Failure error={qr.error} retry={() => void qr.refetch()} />
          ) : qr.isPending || !qr.data ? (
            <p role="status">{t.loading}</p>
          ) : (
            <Image
              unoptimized
              width={296}
              height={296}
              src={qr.data.image_data_url}
              alt={t.qr}
              className="max-w-full"
            />
          )}
        </div>
      )}
    </section>
  );
}

export function ReservationDetail({ id }: { id: string }) {
  const cache = useQueryClient();
  const result = useQuery({
    queryKey: ["reservations", id],
    queryFn: () => reservationApi.detail(id),
    refetchInterval: 30_000,
  });
  const action = useMutation({
    mutationFn: () => reservationApi.cancel(id),
    onSuccess: async () => {
      cache.removeQueries({ queryKey: ["reservation-credential", id] });
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["reservations"] }),
        cache.invalidateQueries({ queryKey: ["catalog"] }),
        cache.invalidateQueries({ queryKey: ["recommendations"] }),
        cache.invalidateQueries({ queryKey: ["search"] }),
        cache.invalidateQueries({ queryKey: ["reader-summary"] }),
        cache.invalidateQueries({ queryKey: ["notifications"] }),
        cache.invalidateQueries({ queryKey: ["favorites"] }),
      ]);
    },
  });
  const row = result.data;
  return (
    <CatalogShell title={t.detail}>
      <Link
        className="mb-6 inline-block text-primary underline"
        href="/reservations"
      >
        {t.title}
      </Link>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        row && (
          <>
            <h2 className="text-2xl font-semibold">
              <Link href={`/books/${row.book_id}`}>{row.book_title}</Link>
            </h2>
            <dl className="my-6 grid gap-5 sm:grid-cols-2">
              {[
                [t.number, row.reservation_number],
                [t.status, t.states[row.status]],
                [t.created, new Date(row.reserved_at).toLocaleString("kk-KZ")],
                ...(row.expires_at
                  ? [
                      [
                        t.expires,
                        new Date(row.expires_at).toLocaleString("kk-KZ"),
                      ],
                    ]
                  : []),
                ...(row.queue_position !== null
                  ? [[t.position, String(row.queue_position)]]
                  : []),
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-sm text-muted-foreground">{label}</dt>
                  <dd className="mt-1 font-medium">{value}</dd>
                </div>
              ))}
            </dl>
            {row.status === "WAITING" && (
              <p className="max-w-2xl">{t.queueNote}</p>
            )}
            {row.status === "READY" && (
              <PrivateQR key={`${row.id}:${row.expires_at}`} row={row} />
            )}
            {action.isSuccess && (
              <p role="status" className="mt-6">
                {action.data?.status === "EXPIRED" ? t.expired : t.cancelled}
              </p>
            )}
            {action.isError && <Failure error={action.error} />}
            {(row.status === "WAITING" || row.status === "READY") && (
              <Button
                variant="outline"
                className="mt-8"
                disabled={action.isPending}
                onClick={() => {
                  if (window.confirm(t.confirm)) action.mutate();
                }}
              >
                {action.isPending ? t.loading : t.cancel}
              </Button>
            )}
          </>
        )
      )}
    </CatalogShell>
  );
}
