"use client";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BookOpen,
  Bookmark,
  CalendarDays,
  Clock3,
  Info,
  ListOrdered,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Cover } from "@/components/books/book-card";
import { catalogApi } from "@/features/catalog/api";
import { CatalogShell, Failure } from "@/features/catalog/shared";
import libraryBooks from "@/features/reader/assets/profile-books.png";
import { reservations as t } from "@/locales/reservations";
import { reservationApi, type Reservation } from "./api";
import styles from "./detail.module.css";

function ReservationHero() {
  return (
    <div className={styles.hero}>
      <div className={styles.intro}>
        <Link className={styles.back} href="/reservations">
          <ArrowLeft aria-hidden="true" />
          {t.title}
        </Link>
        <p className={styles.title} aria-hidden="true">
          {t.detail}
        </p>
        <p className={styles.subtitle}>
          Сіздің бронь мәліметтері мен кітапты алу үшін қажет QR коды.
        </p>
      </div>
      <div className={styles.artwork} aria-hidden="true">
        <Image
          src={libraryBooks}
          alt=""
          width={1536}
          height={1024}
          sizes="(max-width: 767px) 1px, 340px"
        />
        <div className={styles.motto}>
          <BookOpen />
          <p>Жақсы кітаптар әрқашан жақсы адамдарды табады.</p>
          <span />
        </div>
      </div>
    </div>
  );
}

function ReservationCover({ row }: { row: Reservation }) {
  // ReservationRead has no cover URL; reuse the existing catalog query/cache.
  const book = useQuery({
    queryKey: ["catalog", "book", row.book_id],
    queryFn: () => catalogApi.book(row.book_id),
    retry: false,
  });
  return (
    <div className={styles.cover}>
      {book.data ? (
        <Cover book={book.data} />
      ) : (
        <div className={styles.coverFallback}>
          <BookOpen aria-label="Мұқаба жоқ" />
        </div>
      )}
    </div>
  );
}

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
    return row.status === "READY" ? (
      <p role="status" className={styles.notice}>
        <Clock3 aria-hidden="true" />
        {t.expired}
      </p>
    ) : null;
  return (
    <section className={styles.qrSection} aria-label={t.qr}>
      <div className={styles.qrFrame}>
        {shown ? (
          <div className={styles.qrImage}>
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
                className={styles.qrCode}
              />
            )}
          </div>
        ) : (
          <div className={styles.qrHidden}>
            <ShieldCheck aria-hidden="true" />
            <span>QR код жасырылған</span>
          </div>
        )}
      </div>
      <div className={styles.qrCopy}>
        <ScanLine className={styles.scanIcon} aria-hidden="true" />
        <h3>Кітапты алу үшін QR кодты көрсетіңіз</h3>
        <p>{t.pickup}</p>
        <p>{t.qrPrivate}</p>
        <Button
          className={styles.primaryButton}
          variant="outline"
          onClick={() => setShown(!shown)}
        >
          <ScanLine aria-hidden="true" />
          {shown ? t.hideQR : t.showQR}
        </Button>
      </div>
    </section>
  );
}

function ReservationMetadata({ row }: { row: Reservation }) {
  return (
    <dl className={styles.metadata}>
      {[
        { label: t.number, value: row.reservation_number, Icon: Bookmark },
        { label: t.status, value: t.states[row.status], Icon: BookOpen },
        {
          label: t.created,
          value: new Date(row.reserved_at).toLocaleString("kk-KZ"),
          Icon: CalendarDays,
        },
        ...(row.expires_at
          ? [
              {
                label: t.expires,
                value: new Date(row.expires_at).toLocaleString("kk-KZ"),
                Icon: Clock3,
              },
            ]
          : []),
        ...(row.queue_position !== null
          ? [
              {
                label: t.position,
                value: String(row.queue_position),
                Icon: ListOrdered,
              },
            ]
          : []),
      ].map(({ label, value, Icon }) => (
        <div key={label} className={styles.metaItem}>
          <div className={styles.metaIcon} aria-hidden="true">
            <Icon />
          </div>
          <dt>{label}</dt>
          <dd>
            {label === t.status ? (
              <span className={styles.status} data-state={row.status}>
                {value}
              </span>
            ) : (
              value
            )}
          </dd>
        </div>
      ))}
    </dl>
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
    <div className={styles.page}>
      <CatalogShell title={t.detail}>
        <div className={styles.content}>
          <ReservationHero />
          {result.isPending ? (
            <p role="status" className={styles.loading}>
              {t.loading}
            </p>
          ) : result.isError ? (
            <Failure error={result.error} retry={() => void result.refetch()} />
          ) : (
            row && (
              <>
                <div className={styles.card}>
                  <div className={styles.bookSummary}>
                    <ReservationCover row={row} />
                    <div className={styles.bookInfo}>
                      <h2>
                        <Link href={`/books/${row.book_id}`}>
                          {row.book_title}
                        </Link>
                      </h2>
                      <ReservationMetadata row={row} />
                    </div>
                  </div>
                  {row.status === "WAITING" && (
                    <p className={styles.notice}>
                      <ListOrdered aria-hidden="true" />
                      {t.queueNote}
                    </p>
                  )}
                  {row.status === "READY" && (
                    <PrivateQR key={`${row.id}:${row.expires_at}`} row={row} />
                  )}
                </div>
                {action.isSuccess && (
                  <p role="status" className={styles.notice}>
                    {action.data?.status === "EXPIRED"
                      ? t.expired
                      : t.cancelled}
                  </p>
                )}
                {action.isError && <Failure error={action.error} />}
                <div className={styles.actions}>
                  {(row.status === "WAITING" || row.status === "READY") && (
                    <Button
                      variant="outline"
                      className={styles.cancelButton}
                      disabled={action.isPending}
                      onClick={() => {
                        if (window.confirm(t.confirm)) action.mutate();
                      }}
                    >
                      <ArrowLeft aria-hidden="true" />
                      {action.isPending ? t.loading : t.cancel}
                    </Button>
                  )}
                  {row.status === "READY" && (
                    <p className={styles.deadlineNote}>
                      <Info aria-hidden="true" />
                      Алу мерзімі аяқталғаннан кейін QR код жарамсыз болады.
                    </p>
                  )}
                </div>
              </>
            )
          )}
        </div>
      </CatalogShell>
    </div>
  );
}
