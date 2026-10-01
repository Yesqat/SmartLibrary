"use client";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { CatalogShell, Failure } from "@/features/catalog/shared";
import { useAuth } from "@/features/auth/auth-provider";
import { reservationApi } from "@/features/reservations/api";
import { reservations as rt } from "@/locales/reservations";
import { reader as t } from "@/locales/reader";
import { logout } from "@/services/api-client";
import { readerApi, readerDate } from "./api";
import { LoanCard } from "./loans";
import { RecommendationSection } from "@/features/recommendations/section";
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
    <CatalogShell title={`${t.greeting}, ${user?.first_name ?? ""}`}>
      <div className="mb-8 flex flex-wrap items-center gap-4">
        <Link className="text-primary underline" href="/account/profile">
          {t.profile}
        </Link>
        <Link className="text-primary underline" href="/account/security">
          {t.security}
        </Link>
        <Button
          variant="outline"
          disabled={exit.isPending}
          onClick={() => exit.mutate()}
        >
          {t.logout}
        </Button>
      </div>
      {exit.isError && <Failure error={exit.error} />}
      {summary.isPending ? (
        <p role="status">{t.loading}</p>
      ) : summary.isError ? (
        <Failure error={summary.error} retry={() => void summary.refetch()} />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              [t.loans, summary.data.active_borrowings, "/my-books"],
              [
                t.reservations,
                summary.data.active_reservations,
                "/reservations",
              ],
              [t.favorites, summary.data.favorites, "/favorites"],
              [t.unread, summary.data.unread_notifications, "/notifications"],
            ].map(([label, value, href]) => (
              <Link
                key={String(href)}
                href={String(href)}
                className="rounded-xl border bg-white p-5"
              >
                <p>{label}</p>
                <p className="mt-2 text-3xl font-semibold">{value}</p>
              </Link>
            ))}
          </div>
          <p className="my-5">
            {t.nearest}:{" "}
            {summary.data.nearest_due_at
              ? readerDate(summary.data.nearest_due_at)
              : t.noDue}
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
      <section className="mt-8">
        <h2 className="mb-4 text-2xl font-semibold">{t.loans}</h2>
        {loans.isPending ? (
          <p role="status">{t.loading}</p>
        ) : loans.isError ? (
          <Failure error={loans.error} retry={() => void loans.refetch()} />
        ) : (
          <>
            {!loans.data.total && <p>{t.empty}</p>}
            <div className="grid gap-4 md:grid-cols-2">
              {loans.data.items.slice(0, 4).map((loan) => (
                <LoanCard key={loan.id} loan={loan} />
              ))}
            </div>
            <Link
              href="/my-books"
              className="mt-4 inline-block text-primary underline"
            >
              {t.all}
            </Link>
          </>
        )}
      </section>
      <section className="mt-8">
        <h2 className="mb-4 text-2xl font-semibold">{t.reservations}</h2>
        {reservations.isPending ? (
          <p role="status">{t.loading}</p>
        ) : reservations.isError ? (
          <Failure
            error={reservations.error}
            retry={() => void reservations.refetch()}
          />
        ) : (
          <>
            {!reservations.data.total && <p>{t.empty}</p>}
            <ul className="grid gap-4 md:grid-cols-2">
              {reservations.data.items.slice(0, 4).map((row) => (
                <li key={row.id} className="rounded-xl border bg-white p-5">
                  <Link
                    href={`/reservations/${row.id}`}
                    className="font-semibold text-primary underline"
                  >
                    {row.book_title}
                  </Link>
                  <p className="mt-2">{rt.states[row.status]}</p>
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
      <RecommendationSection kind="personalized" />
    </CatalogShell>
  );
}
