"use client";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { CatalogShell, Failure } from "@/features/catalog/shared";
import { useAuth } from "@/features/auth/auth-provider";
import { logout } from "@/services/api-client";
import { admin as t } from "@/locales/admin";
import { reader as rt } from "@/locales/reader";
import { kk } from "@/locales/kk";
import { adminApi } from "./api";
import { OverviewPanel } from "@/features/analytics/panels";
export function AdminDashboard() {
  const { user } = useAuth(),
    result = useQuery({
      queryKey: ["admin-dashboard"],
      queryFn: adminApi.dashboard,
      refetchInterval: 30000,
    }),
    exit = useMutation({ mutationFn: logout });
  return (
    <CatalogShell title={t.dashboard}>
      <section className="mb-6 rounded-xl border p-5">
        <h2 className="text-lg font-semibold">{kk.auth.account}</h2>
        <p>
          {user?.first_name} {user?.last_name} · {user?.email}
        </p>
        <p>{kk.auth.admin}</p>
        <div className="mt-4 flex gap-4">
          <Link className="text-primary underline" href="/account/profile">
            {rt.profile}
          </Link>
          <Button
            variant="outline"
            disabled={exit.isPending}
            onClick={() => exit.mutate()}
          >
            {rt.logout}
          </Button>
        </div>
        {exit.isError && <Failure error={exit.error} />}
      </section>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(result.data).map(([key, value]) => (
            <div className="rounded-xl border bg-white p-5" key={key}>
              <dt>{t.metrics[key as keyof typeof t.metrics]}</dt>
              <dd className="mt-2 text-3xl font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
      )}
      <section className="mt-8">
        <OverviewPanel chartsOnly />
      </section>
    </CatalogShell>
  );
}
