"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { admin as t } from "@/locales/admin";
export function AdminNavigation() {
  const path = usePathname();
  return (
    <nav
      aria-label={t.dashboard}
      className="mb-6 flex flex-wrap gap-2 xl:flex-col"
    >
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
          className={`rounded-lg px-3 py-2 text-sm ${path === href ? "bg-primary text-white" : "bg-white text-primary hover:bg-emerald-50"}`}
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
