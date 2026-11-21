"use client";
import Link from "next/link";
import Image from "next/image";
import {
  Bell,
  BookOpen,
  Bookmark,
  CalendarDays,
  Clock3,
  Heart,
} from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { LibrarianModel } from "@/components/assistant/librarian-model";
import { CatalogNavigation, Failure } from "@/features/catalog/shared";
import { useAuth } from "@/features/auth/auth-provider";
import { reservationApi } from "@/features/reservations/api";
import { reservations as rt } from "@/locales/reservations";
import { reader as t } from "@/locales/reader";
import { catalog } from "@/locales/catalog";
import { logout } from "@/services/api-client";
import { readerApi, readerDate } from "./api";
import { LoanCard } from "./loans";
import { RecommendationSection } from "@/features/recommendations/section";
import { ReaderCard } from "./reader-card";
import styles from "./dashboard.module.css";
export function ReaderDashboard() {
  const { user } = useAuth();
  const summary = useQuery({
    queryKey: ["reader-summary"],
    queryFn: readerApi.summary,
    refetchInterval: 30000,
  });
  const loans = useQuery({
    queryKey: ["borrowings", false, 1],
    queryFn: () => readerApi.loans(1),
    refetchInterval: 30000,
  });
  const reservations = useQuery({
    queryKey: ["reservations", "dashboard"],
    queryFn: () => reservationApi.list(1, "", true),
    refetchInterval: 30000,
  });
  const exit = useMutation({ mutationFn: logout });
  return (
    <div className={styles.dashboard}>
      <CatalogNavigation currentHref="/dashboard" />
      <main>
        <section className={styles.hero} aria-labelledby="dashboard-greeting">
          <div className={styles.backdrop} aria-hidden="true" />
          <div className={styles.welcome}>
            <p className={styles.eyebrow}>{catalog.account}</p>
            <h1 id="dashboard-greeting">
              {t.greeting}, {user?.first_name ?? ""}
            </h1>
            <div className={styles.actions}>
              <Link className={styles.primaryAction} href="/account/profile">
                {t.profile}
              </Link>
              <Link className={styles.secondaryAction} href="/account/security">
                {t.security}
              </Link>
              <Button
                variant="outline"
                className={styles.secondaryAction}
                disabled={exit.isPending}
                onClick={() => exit.mutate()}
              >
                {t.logout}
              </Button>
            </div>
            {exit.isError && <Failure error={exit.error} />}
          </div>
          <div className={styles.art} aria-hidden="true">
            <div className={styles.ticket}>
              <ReaderCard />
            </div>
            <LibrarianModel mode="account" className={styles.figure} />
          </div>
        </section>
        <div className={styles.content}>
          {summary.isPending ? (
            <p role="status">{t.loading}</p>
          ) : summary.isError ? (
            <Failure
              error={summary.error}
              retry={() => void summary.refetch()}
            />
          ) : (
            <>
              <div className={styles.stats}>
                {[
                  {
                    label: t.loans,
                    value: summary.data.active_borrowings,
                    href: "/my-books",
                    Icon: BookOpen,
                  },
                  {
                    label: t.reservations,
                    value: summary.data.active_reservations,
                    href: "/reservations",
                    Icon: Bookmark,
                  },
                  {
                    label: t.favorites,
                    value: summary.data.favorites,
                    href: "/favorites",
                    Icon: Heart,
                  },
                  {
                    label: t.unread,
                    value: summary.data.unread_notifications,
                    href: "/notifications",
                    Icon: Bell,
                  },
                ].map(({ label, value, href, Icon }) => (
                  <Link key={href} href={href} className={styles.stat}>
                    <span className={styles.statIcon}>
                      <Icon aria-hidden="true" />
                    </span>
                    <div>
                      <p>{label}</p>
                      <p className={styles.statValue}>{value}</p>
                    </div>
                  </Link>
                ))}
              </div>
              <p className={styles.nearest}>
                <Clock3 aria-hidden="true" />
                <span>
                  {t.nearest}:{" "}
                  <strong>
                    {summary.data.nearest_due_at
                      ? readerDate(summary.data.nearest_due_at)
                      : t.noDue}
                  </strong>
                </span>
              </p>
              {summary.data.overdue_borrowings > 0 && (
                <p
                  role="alert"
                  className="mb-6 rounded-xl bg-red-50 p-4 text-red-900"
                >
                  {t.overdue}: {summary.data.overdue_borrowings}.{" "}
                  {t.returnInstruction}
                </p>
              )}
            </>
          )}
          <section className={styles.section} aria-labelledby="dashboard-loans">
            <div className={styles.sectionHeading}>
              <h2 id="dashboard-loans">{t.loans}</h2>
              {!loans.isPending && !loans.isError && (
                <Link href="/my-books" className={styles.viewAll}>
                  Барлығын көру
                </Link>
              )}
            </div>
            {loans.isPending ? (
              <p role="status">{t.loading}</p>
            ) : loans.isError ? (
              <Failure error={loans.error} retry={() => void loans.refetch()} />
            ) : (
              <>
                {!loans.data.total && (
                  <div className={styles.empty}>
                    <BookOpen aria-hidden="true" />
                    <p>{t.empty}</p>
                  </div>
                )}
                <div className={styles.loans}>
                  {loans.data.items.slice(0, 4).map((loan) => (
                    <div key={loan.id} className={styles.loanCard}>
                      <div className={styles.cover}>
                        {loan.cover_url ? (
                          <Image
                            src={loan.cover_url}
                            alt={loan.book_title}
                            fill
                            unoptimized
                            sizes="(max-width: 374px) 84px, 120px"
                          />
                        ) : (
                          <BookOpen aria-label={catalog.noCover} />
                        )}
                      </div>
                      <LoanCard loan={loan} />
                    </div>
                  ))}
                </div>
              </>
            )}
          </section>
          <section
            className={styles.section}
            aria-labelledby="dashboard-reservations"
          >
            <div className={styles.sectionHeading}>
              <h2 id="dashboard-reservations">{t.reservations}</h2>
            </div>
            {reservations.isPending ? (
              <p role="status">{t.loading}</p>
            ) : reservations.isError ? (
              <Failure
                error={reservations.error}
                retry={() => void reservations.refetch()}
              />
            ) : (
              <>
                {!reservations.data.total && (
                  <div className={styles.empty}>
                    <CalendarDays aria-hidden="true" />
                    <p>{t.empty}</p>
                    <p className={styles.emptyHint}>
                      Ұнаған кітаптарыңызды брондап, оқуға мүмкіндік алыңыз.
                    </p>
                  </div>
                )}
                <ul className={styles.reservations}>
                  {reservations.data.items.slice(0, 4).map((row) => (
                    <li key={row.id} className={styles.reservationCard}>
                      <Link
                        href={`/reservations/${row.id}`}
                        className="font-semibold text-primary underline"
                      >
                        {row.book_title}
                      </Link>
                      <p className={styles.reservationStatus}>
                        {rt.states[row.status]}
                      </p>
                      {row.qr_available && (
                        <Link
                          href={`/reservations/${row.id}`}
                          className="mt-3 inline-block text-primary underline"
                        >
                          {rt.showQR}
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
          <div className={styles.recommendations}>
            <RecommendationSection kind="personalized" />
          </div>
        </div>
      </main>
    </div>
  );
}
