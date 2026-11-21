"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { admin as t } from "@/locales/admin";
import styles from "@/features/catalog/workspace.module.css";
export function AdminNavigation() {
  const path = usePathname();
  return (
    <nav aria-label={t.dashboard} className={styles.adminNavigation}>
      {[
        ["/admin", t.dashboard],
        ["/admin/users", t.users],
        ["/admin/librarians", t.librarians],
        ["/admin/books", t.books],
        ["/admin/authors", t.authors],
        ["/admin/categories", t.categories],
        ["/admin/publishers", t.publishers],
        ["/admin/category-predictions", "Санат ұсыныстары"],
        ["/admin/analytics", "Талдау"],
        ["/admin/reports", "Есептер"],
        ["/admin/ai", "AI қызметтеріне шолу"],
        ["/admin/inventory", t.inventory],
        ["/admin/borrowings", t.borrowings],
        ["/admin/reservations", t.reservations],
        ["/admin/settings", t.settings],
        ["/admin/audit-logs", t.audit],
      ].map(([href, label]) => (
        <Link
          key={href}
          href={href}
          aria-current={path === href ? "page" : undefined}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}
