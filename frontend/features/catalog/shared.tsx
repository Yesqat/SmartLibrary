"use client";
import Link from "next/link";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";
import { catalog as t } from "@/locales/catalog";
import { kk } from "@/locales/kk";
import { reader as rt } from "@/locales/reader";
import { ApiError } from "@/services/api-client";
import { AdminNavigation } from "@/features/admin/navigation";
export const inputClass =
  "w-full rounded-lg border bg-white px-3 py-2 text-foreground";
export function CatalogShell({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const { user } = useAuth();
  const account =
    user?.role === "ADMIN"
      ? "/admin"
      : user?.role === "LIBRARIAN"
        ? "/librarian"
        : "/dashboard";
  return (
    <main className="mx-auto max-w-6xl px-5 py-10">
      <nav
        aria-label={t.title}
        className="mb-10 flex flex-wrap gap-5 text-sm text-primary"
      >
        <Link href="/">SmartLibrary</Link>
        <Link href="/catalog">{t.title}</Link>
        {user?.role === "LIBRARIAN" && (
          <Link href="/librarian/qr">Броньді тексеру</Link>
        )}
        {user?.role === "READER" && (
          <>
            <Link href="/reservations">{rt.reservations}</Link>
            <Link href="/my-books">{rt.loans}</Link>
            <Link href="/favorites">{rt.favorites}</Link>
            <Link href="/notifications">{rt.notifications}</Link>
            <Link href="/assistant">AI кітапханашы</Link>
          </>
        )}
        <Link href={user ? account : "/login"}>
          {user ? t.account : kk.auth.login}
        </Link>
        {user && <Link href="/account/profile">{rt.profile}</Link>}
        {user && user.role !== "READER" && (
          <>
            <Link href={`${account}/books`}>{t.staff}</Link>
            <Link href={`${account}/references`}>{t.references}</Link>
            {user.role === "LIBRARIAN" && (
              <>
                <Link href="/librarian/issue">Кітап беру</Link>
                <Link href="/librarian/return">Кітап қабылдау</Link>
                <Link href="/librarian/readers">Оқырмандар</Link>
                <Link href="/librarian/reservations">Броньдар</Link>
                <Link href="/librarian/overdue">Мерзімі өткендер</Link>
                <Link href="/librarian/category-predictions">
                  Санат ұсыныстары
                </Link>
              </>
            )}
          </>
        )}
      </nav>
      <h1 className="mb-8 text-3xl font-semibold">{title}</h1>
      <div
        className={
          user?.role === "ADMIN"
            ? "grid gap-7 xl:grid-cols-[190px_minmax(0,1fr)]"
            : undefined
        }
      >
        {user?.role === "ADMIN" && <AdminNavigation />}
        <div className="min-w-0">{children}</div>
      </div>
    </main>
  );
}
export function Failure({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="my-4 rounded-lg border border-red-300 bg-red-50 p-4 text-red-900"
    >
      <p>{error instanceof ApiError ? error.message : kk.error}</p>
      {retry && (
        <Button variant="outline" className="mt-3" onClick={retry}>
          {t.retry}
        </Button>
      )}
    </div>
  );
}
export function Pager({
  page,
  pages,
  onChange,
}: {
  page: number;
  pages: number;
  onChange: (value: number) => void;
}) {
  return (
    <nav
      aria-label={t.page}
      className="mt-8 flex items-center justify-center gap-4"
    >
      <Button
        variant="outline"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        {t.previous}
      </Button>
      <span>
        {t.page} {page} / {Math.max(1, pages)}
      </span>
      <Button
        variant="outline"
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
      >
        {t.next}
      </Button>
    </nav>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="grid gap-2 text-sm font-medium">
      {label}
      {children}
    </label>
  );
}
