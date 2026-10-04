"use client";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  BookOpen,
  CalendarClock,
  CalendarX2,
  Check,
  CheckCheck,
  Clock,
  ClockAlert,
  Inbox,
  Sprout,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { CatalogShell, Failure, Pager } from "@/features/catalog/shared";
import { reader as t } from "@/locales/reader";
import {
  notificationLink,
  readerApi,
  readerDate,
  type Notification,
} from "./api";
import notificationBooks from "./assets/notification-books.png";
import styles from "./notifications.module.css";

function NotificationsHero() {
  return (
    <div className={styles.hero}>
      <div className={styles.heroInner}>
        <div className={styles.intro}>
          <p className={styles.eyebrow}>ХАБАРЛАМАЛАР</p>
          <p className={styles.title} aria-hidden="true">
            {t.notifications}
          </p>
          <p className={styles.description}>
            Кітапханаңыздағы маңызды жаңалықтар мен ескертулерді осы жерден
            қараңыз.
          </p>
        </div>
        <div className={styles.artwork} aria-hidden="true">
          <Image
            src={notificationBooks}
            alt=""
            width={1536}
            height={1024}
            sizes="(max-width: 767px) 1px, (max-width: 1199px) 40vw, 400px"
            loading="eager"
          />
          <div className={styles.motto}>
            <Sprout />
            <p>Уақытылы ақпарат — үлкен мүмкіндік!</p>
            <span />
          </div>
        </div>
      </div>
    </div>
  );
}

function NotificationIcon({ type }: { type: Notification["type"] }) {
  const Icon =
    {
      RESERVATION_READY: BookOpen,
      RESERVATION_EXPIRING: CalendarClock,
      RESERVATION_EXPIRED: CalendarX2,
      DUE_SOON: BookOpen,
      OVERDUE: ClockAlert,
    }[type] ?? Bell;
  return <Icon aria-hidden="true" />;
}
export function Notifications() {
  const [page, setPage] = useState(1),
    [unread, setUnread] = useState(false);
  const cache = useQueryClient();
  const result = useQuery({
    queryKey: ["notifications", page, unread],
    queryFn: () => readerApi.notifications(page, unread),
    refetchInterval: 30000,
  });
  const mutation = useMutation({
    mutationFn: async (id: string | null) => {
      if (id) await readerApi.read(id);
      else await readerApi.readAll();
    },
    onSuccess: async () => {
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["notifications"] }),
        cache.invalidateQueries({ queryKey: ["reader-summary"] }),
      ]);
    },
  });
  return (
    <div className={styles.notifications}>
      <CatalogShell title={t.notifications}>
        <NotificationsHero />
        <div className={styles.workspace}>
          <aside className={styles.sidebar} aria-label="Хабарлама сүзгісі">
            <h2 className={styles.filterHeading}>
              <Bell aria-hidden="true" />
              <span>{unread ? t.unread : "Барлық хабарламалар"}</span>
              {result.data && (
                <span
                  className={styles.count}
                  aria-label={
                    unread ? "Оқылмаған хабарламалар саны" : "Хабарламалар саны"
                  }
                >
                  {result.data.total}
                </span>
              )}
            </h2>
            <label className={styles.unreadFilter}>
              <input
                type="checkbox"
                checked={unread}
                onChange={(e) => {
                  setUnread(e.target.checked);
                  setPage(1);
                }}
              />
              <span>{t.unread}</span>
            </label>
            <div className={styles.bulkAction}>
              <Button
                variant="outline"
                className={styles.readAll}
                disabled={mutation.isPending || !result.data?.total}
                onClick={() => mutation.mutate(null)}
              >
                <CheckCheck aria-hidden="true" />
                {t.readAll}
              </Button>
            </div>
            <div className={styles.helper}>
              <Sprout aria-hidden="true" />
              <p>
                Хабарламаларды уақытында қадағалап, кітапхана мүмкіндіктерін
                толық пайдаланыңыз!
              </p>
            </div>
          </aside>
          <section className={styles.feed} aria-label={t.notifications}>
            {mutation.isError && <Failure error={mutation.error} />}
            {mutation.isSuccess && (
              <p role="status" className={styles.success}>
                <Check aria-hidden="true" />
                {t.readDone}
              </p>
            )}
            {result.isPending ? (
              <p role="status" className={styles.loading}>
                {t.loading}
              </p>
            ) : result.isError ? (
              <Failure
                error={result.error}
                retry={() => void result.refetch()}
              />
            ) : (
              <>
                {!result.data.total && (
                  <div className={styles.empty}>
                    <Inbox aria-hidden="true" />
                    <p>{t.empty}</p>
                  </div>
                )}
                <ul className={styles.list}>
                  {result.data.items.map((row) => (
                    <li
                      key={row.id}
                      className={`${styles.notification} ${row.is_read ? styles.readNotification : styles.unreadNotification}`}
                    >
                      <div className={styles.iconBadge}>
                        <NotificationIcon type={row.type} />
                        {!row.is_read && (
                          <span
                            className={styles.unreadDot}
                            role="img"
                            aria-label={t.unread}
                          />
                        )}
                      </div>
                      <div className={styles.message}>
                        <h2>{row.title}</h2>
                        <p>{row.message}</p>
                        <div className={styles.timestamp}>
                          <Clock aria-hidden="true" />
                          <time dateTime={row.created_at}>
                            {readerDate(row.created_at)}
                          </time>
                        </div>
                      </div>
                      <div className={styles.actions}>
                        <Link
                          className={styles.open}
                          href={notificationLink(row)}
                        >
                          {t.open}
                        </Link>
                        {!row.is_read && (
                          <Button
                            variant="outline"
                            className={styles.readAction}
                            disabled={mutation.isPending}
                            onClick={() => mutation.mutate(row.id)}
                          >
                            {t.read}
                          </Button>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
                <Pager
                  page={page}
                  pages={result.data.pages}
                  onChange={setPage}
                />
              </>
            )}
          </section>
        </div>
      </CatalogShell>
    </div>
  );
}
