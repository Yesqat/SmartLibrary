"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { BookCard } from "@/components/books/book-card";
import { Button } from "@/components/ui/button";
import { catalog as t } from "@/locales/catalog";
import { catalogApi } from "./api";
import { CatalogShell, Failure, inputClass, Pager } from "./shared";
import styles from "./catalog.module.css";
export function CatalogList({ staffRoot }: { staffRoot?: string }) {
  const [page, setPage] = useState(1),
    [query, setQuery] = useState(""),
    [draft, setDraft] = useState(""),
    [archived, setArchived] = useState(false);
  const result = useQuery({
    queryKey: ["catalog", "books", page, query, archived],
    queryFn: () => catalogApi.books(page, query, archived),
  });
  return (
    <CatalogShell title={t.title}>
      <div className={styles.staffTools}>
        <form
          className="flex min-w-0 grow gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(draft.trim());
            setPage(1);
          }}
        >
          <label className="min-w-0 grow">
            <span className="sr-only">{t.search}</span>
            <input
              className={inputClass}
              value={draft}
              maxLength={500}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={t.search}
            />
          </label>
          <Button type="submit">{t.find}</Button>
        </form>
        {staffRoot && (
          <>
            <Button asChild>
              <Link href={`${staffRoot}/books/new`}>{t.add}</Link>
            </Button>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={archived}
                onChange={(e) => {
                  setArchived(e.target.checked);
                  setPage(1);
                }}
              />
              {t.includeArchived}
            </label>
          </>
        )}
      </div>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {result.data.items.length ? (
            <div className={styles.books}>
              {result.data.items.map((book) => (
                <BookCard key={book.id} book={book} staffRoot={staffRoot} />
              ))}
            </div>
          ) : (
            <p className={styles.empty}>{t.empty}</p>
          )}
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
