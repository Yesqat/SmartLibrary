"use client";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { CatalogShell, Failure } from "@/features/catalog/shared";
import { useAuth } from "@/features/auth/auth-provider";
import { logout } from "@/services/api-client";
import { readerDate } from "@/features/reader/api";
import { librarian as t } from "@/locales/librarian";
import { reader as rt } from "@/locales/reader";
import { kk } from "@/locales/kk";
import { librarianApi } from "./api";
import styles from "@/features/catalog/workspace.module.css";
export function LibrarianDashboard() {
  const { user } = useAuth();
  const result = useQuery({
    queryKey: ["librarian-dashboard"],
    queryFn: librarianApi.dashboard,
    refetchInterval: 30000,
  });
  const exit = useMutation({ mutationFn: logout });
  return (
    <CatalogShell title={t.dashboard}>
      <section className={styles.account}>
        <h2 className="text-lg font-semibold">{kk.auth.account}</h2>
        <p>
          {user?.first_name} {user?.last_name} · {user?.email}
        </p>
        <p>{kk.auth.librarian}</p>
        <Button
          className="mt-4"
          variant="outline"
          disabled={exit.isPending}
          onClick={() => exit.mutate()}
        >
          {rt.logout}
        </Button>
        {exit.isError && <Failure error={exit.error} />}
      </section>
      <div className="mb-8 flex flex-wrap gap-3">
        {[
          ["/librarian/qr", t.camera],
          ["/librarian/issue", "Кітап беру"],
          ["/librarian/return", "Кітап қабылдау"],
          ["/librarian/books/new", "Кітап қосу"],
          ["/account/profile", rt.profile],
        ].map(([href, label]) => (
          <Button asChild variant="outline" key={href}>
            <Link href={href}>{label}</Link>
          </Button>
        ))}
      </div>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          <p className="mb-4 text-sm">
            {t.timezone}: {result.data.timezone}
          </p>
          <dl className={styles.metrics}>
            {[
              [t.issued, result.data.issued_today],
              [t.returned, result.data.returned_today],
              [t.newReservations, result.data.new_reservations_today],
              [t.activeReservations, result.data.active_reservations],
              [t.overdue, result.data.overdue_borrowings],
            ].map(([label, value]) => (
              <div key={String(label)}>
                <dt>{label}</dt>
                <dd className="mt-2 text-3xl font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
          <h2 className="my-6 text-xl font-semibold">{t.operations}</h2>
          {!result.data.recent_operations.length && <p>{t.empty}</p>}
          <ul className="space-y-3">
            {result.data.recent_operations.map((row) => (
              <li key={row.id} className="rounded-xl border p-4">
                {t.actions[row.action as keyof typeof t.actions] ?? row.action}{" "}
                · {readerDate(row.created_at)}
              </li>
            ))}
          </ul>
        </>
      )}
    </CatalogShell>
  );
}
