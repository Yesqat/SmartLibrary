"use client";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { kk } from "@/locales/kk";
import { ApiError, logout } from "@/services/api-client";
import { useAuth } from "./auth-provider";

export function AccountSummary() {
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!user) return null;
  const roles = {
    READER: kk.auth.reader,
    LIBRARIAN: kk.auth.librarian,
    ADMIN: kk.auth.admin,
  };
  return (
    <main className="mx-auto max-w-4xl px-6 py-14">
      <Link href="/" className="text-primary">
        {kk.name}
      </Link>
      <p className="mt-12 text-sm text-muted-foreground">{kk.auth.dashboard}</p>
      <h1 className="mt-3 text-4xl font-semibold">
        {kk.auth.greeting}, {user.first_name}
      </h1>
      <section className="mt-8 rounded-2xl border border-border p-6">
        <h2 className="text-xl font-semibold">{kk.auth.account}</h2>
        <dl className="mt-5 grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm text-muted-foreground">{kk.auth.email}</dt>
            <dd>{user.email}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">{kk.auth.role}</dt>
            <dd>{roles[user.role]}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">{kk.auth.status}</dt>
            <dd>{kk.auth.active}</dd>
          </div>
        </dl>
      </section>
      <div className="mt-6 flex flex-wrap gap-4">
        {user.role === "LIBRARIAN" && (
          <Button asChild>
            <Link href="/librarian/qr">Броньді тексеру</Link>
          </Button>
        )}
        <Button asChild variant="outline">
          <Link href="/catalog">Кітаптар каталогы</Link>
        </Button>
        {user.role !== "READER" && (
          <Button asChild variant="outline">
            <Link
              href={user.role === "ADMIN" ? "/admin/books" : "/librarian/books"}
            >
              Каталогты басқару
            </Link>
          </Button>
        )}
        {user.role === "READER" && (
          <Button asChild variant="outline">
            <Link href="/reservations">Менің броньдарым</Link>
          </Button>
        )}
        <Button asChild>
          <Link href="/account/security">{kk.auth.security}</Link>
        </Button>
        <Button
          variant="outline"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              await logout();
            } catch (cause) {
              setError(cause instanceof ApiError ? cause.message : kk.error);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? kk.auth.pending : kk.auth.logout}
        </Button>
      </div>
      {error && (
        <p role="alert" className="mt-4 text-destructive">
          {error}
        </p>
      )}
    </main>
  );
}
