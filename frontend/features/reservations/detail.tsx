"use client";
import Image from "next/image";
import Link from "next/link";
import {
  type CSSProperties,
  type RefObject,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  CircleX,
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
import { measureBookCover } from "@/components/books/book-transition-geometry";
import { useAuth } from "@/features/auth/auth-provider";
import { catalogApi } from "@/features/catalog/api";
import { CatalogShell, Failure } from "@/features/catalog/shared";
import { reservations as t } from "@/locales/reservations";
import { reservationApi, type Reservation } from "./api";
import {
  type CreationFeedback,
  matchesCreationFeedback,
  takeCreationFeedback,
} from "./creation-feedback";
import styles from "./detail.module.css";

function placeRibbon(
  cover: HTMLDivElement | null,
  hide: () => void,
  signal: AbortSignal,
): CSSProperties | undefined {
  try {
    const motion = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!cover || !motion || motion.matches) return;
    const art = measureBookCover(cover);
    if (art?.kind !== "image") return;
    const box = cover.getBoundingClientRect();
    const width = Math.min(17, art.rect.width * 0.18);
    const src = art.image.src;
    const observer = new MutationObserver(() => {
      if (!cover.contains(art.image) || art.image.src !== src) hide();
    });
    signal.addEventListener("abort", () => observer.disconnect(), {
      once: true,
    });
    observer.observe(cover, {
      childList: true,
      subtree: true,
      attributeFilter: ["src"],
    });
    window.addEventListener("resize", hide, { signal, once: true });
    motion.addEventListener?.("change", hide, { signal, once: true });
    return {
      left: art.rect.left - box.left + art.rect.width * 0.8 - width / 2,
      top: art.rect.top - box.top,
      width,
      height: Math.min(art.rect.height * 0.34, width * 2.5),
    };
  } catch {
    // The text confirmation also works without measurable artwork.
    return;
  }
}

type Feedback = { status: "READY" | "WAITING"; ribbon?: CSSProperties };

function useCreationFeedback(
  id: string,
  userId: string | undefined,
  result: UseQueryResult<Reservation>,
) {
  const cache = useQueryClient();
  const cover = useRef<HTMLDivElement>(null);
  const pending = useRef<CreationFeedback | null | undefined>(undefined);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const { data: row, isFetchedAfterMount, isSuccess } = result;

  useEffect(() => {
    if (!userId) return;
    if (pending.current === undefined)
      pending.current = takeCreationFeedback(cache, userId, id) ?? null;
    const marker = pending.current;
    if (!marker) return;
    const listeners = new AbortController();
    const { signal } = listeners;
    let timer: number | undefined;
    const stop = () => {
      window.clearTimeout(timer);
      listeners.abort();
      window.removeEventListener("pagehide", dismiss);
    };
    const dismiss = () => {
      pending.current = null;
      setFeedback(null);
      stop();
    };
    window.addEventListener("pagehide", dismiss);

    if (isFetchedAfterMount) {
      // Keep the marker local through Strict Mode's setup/cleanup replay.
      queueMicrotask(() => {
        if (signal.aborted) return;
        pending.current = null;
        if (!isSuccess || !row || !matchesCreationFeedback(marker, userId, row))
          return dismiss();
        if (row.status !== "READY" && row.status !== "WAITING")
          return dismiss();
        // The server also checks the pickup deadline against its own clock.
        if (row.status === "READY" && !row.qr_available) return dismiss();
        const lifetime =
          row.status === "READY"
            ? Math.min(3600, Date.parse(row.expires_at ?? "") - Date.now())
            : 3600;
        if (!(lifetime > 0)) return dismiss();
        const hideRibbon = () => {
          listeners.abort();
          setFeedback((current) =>
            current?.ribbon ? { ...current, ribbon: undefined } : current,
          );
        };
        const ribbon = placeRibbon(cover.current, hideRibbon, signal);
        setFeedback({ status: row.status, ribbon });
        timer = window.setTimeout(dismiss, lifetime);
      });
    }
    return () => {
      stop();
      setFeedback(null);
    };
  }, [cache, id, userId, row, isFetchedAfterMount, isSuccess]);

  return {
    cover,
    feedback: feedback?.status === row?.status ? feedback : null,
  };
}

function ReservationCover({
  row,
  cover,
  ribbon,
}: {
  row: Reservation;
  cover: RefObject<HTMLDivElement | null>;
  ribbon?: CSSProperties;
}) {
  // ReservationRead has no cover URL; reuse the existing catalog query/cache.
  const book = useQuery({
    queryKey: ["catalog", "book", row.book_id],
    queryFn: () => catalogApi.book(row.book_id),
    retry: false,
  });
  return (
    <div className={styles.cover} ref={cover}>
      {book.data ? (
        <Cover book={book.data} />
      ) : (
        <div className={styles.coverFallback}>
          <BookOpen aria-label="Мұқаба жоқ" />
        </div>
      )}
      {ribbon && (
        <span
          className={styles.ribbon}
          data-reservation-ribbon=""
          data-state={row.status}
          aria-hidden="true"
          style={ribbon}
        />
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
  const { user } = useAuth();
  const userId = user?.role === "READER" ? user.id : undefined;
  return (
    <ReservationDetailView
      key={`${id}:${userId ?? ""}`}
      id={id}
      userId={userId}
    />
  );
}

function ReservationDetailView({
  id,
  userId,
}: {
  id: string;
  userId?: string;
}) {
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
  const { cover, feedback } = useCreationFeedback(id, userId, result);
  return (
    <div className={styles.page}>
      <CatalogShell title={t.detail}>
        <div className={styles.content}>
          <div className={styles.intro}>
            <p className={styles.introText}>
              <span className={feedback ? styles.concealed : undefined}>
                Сіздің бронь мәліметтері мен кітапты алу үшін қажет QR коды.
              </span>
              <span
                className={feedback ? styles.created : undefined}
                role="status"
                data-state={feedback?.status}
              >
                {feedback &&
                  (feedback.status === "READY"
                    ? t.createdReady
                    : t.createdWaiting)}
              </span>
            </p>
            <Link className={styles.back} href="/reservations">
              {t.title}
            </Link>
          </div>
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
                    <ReservationCover
                      row={row}
                      cover={cover}
                      ribbon={feedback?.ribbon}
                    />
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
                      <CircleX aria-hidden="true" />
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
