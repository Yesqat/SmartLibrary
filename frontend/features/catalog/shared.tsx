"use client";
import Link from "next/link";
import type { ReactNode, Ref } from "react";
import { CircleAlert, RotateCw } from "lucide-react";
import { BrandMark } from "@/components/ui/brand-mark";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";
import { catalog as t } from "@/locales/catalog";
import { kk } from "@/locales/kk";
import { reader as rt } from "@/locales/reader";
import { ApiError } from "@/services/api-client";
import { AdminNavigation } from "@/features/admin/navigation";
import styles from "./workspace.module.css";

export const inputClass = styles.input;

export function CatalogNavigation({ currentHref }: { currentHref?: string }) {
  const { user } = useAuth();
  const account =
    user?.role === "ADMIN"
      ? "/admin"
      : user?.role === "LIBRARIAN"
        ? "/librarian"
        : "/dashboard";
  return (
    <nav aria-label={t.title} className={styles.navigation}>
      <Link href="/" className={styles.brand}>
        <BrandMark />
        SmartLibrary
      </Link>
      <Link href="/catalog">{t.title}</Link>
      {user?.role === "LIBRARIAN" && (
        <Link href="/librarian/qr">Броньді тексеру</Link>
      )}
      {user?.role === "READER" && (
        <>
          <Link href="/reservations">{rt.reservations}</Link>
          <Link href="/my-books">{rt.loans}</Link>
          <Link href="/favorites" data-favorites-target="">
            {rt.favorites}
          </Link>
          <Link href="/notifications">{rt.notifications}</Link>
          <Link
            href="/assistant"
            aria-current={currentHref === "/assistant" ? "page" : undefined}
          >
            AI кітапханашы
          </Link>
        </>
      )}
      <Link
        className={styles.accountLink}
        href={user ? account : "/login"}
        aria-current={currentHref === account ? "page" : undefined}
      >
        {user ? t.account : kk.auth.login}
      </Link>
      {user && <Link href="/account/profile">{rt.profile}</Link>}
      {user && user.role !== "READER" && (
        <>
          {user.role === "LIBRARIAN" && (
            <span aria-hidden="true" className={styles.navDivider} />
          )}
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
  );
}

export function CatalogShell({
  title,
  titleRef,
  children,
}: {
  title: string;
  titleRef?: Ref<HTMLHeadingElement>;
  children: ReactNode;
}) {
  const { user } = useAuth();
  return (
    <main className={styles.workspace}>
      <CatalogNavigation />
      <h1
        ref={titleRef}
        tabIndex={titleRef ? -1 : undefined}
        className={styles.title}
      >
        {title}
      </h1>
      <div
        className={user?.role === "ADMIN" ? styles.adminLayout : styles.layout}
      >
        {user?.role === "ADMIN" && <AdminNavigation />}
        <div className={styles.content} data-role={user?.role}>
          {children}
        </div>
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
    <div role="alert" className={styles.failure}>
      <CircleAlert aria-hidden="true" />
      <p>{error instanceof ApiError ? error.message : kk.error}</p>
      {retry && (
        <Button variant="outline" onClick={retry}>
          <RotateCw aria-hidden="true" size={16} />
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
    <nav aria-label={t.page} className={styles.pager}>
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
    <label className={styles.field}>
      {label}
      {children}
    </label>
  );
}
