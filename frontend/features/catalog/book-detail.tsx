"use client";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useLayoutEffect, useRef } from "react";
import { useAuth } from "@/features/auth/auth-provider";
import { apiMutation } from "@/services/api-client";
import { Cover } from "@/components/books/book-card";
import { useBookTransition } from "@/components/books/book-transition-provider";
import { catalog as t } from "@/locales/catalog";
import { bookDetailQuery } from "./api";
import { CatalogShell, Failure } from "./shared";
import { ReserveButton } from "@/features/reservations/reserve-button";
import { FavoriteButton } from "@/features/reader/favorites";
import { RecommendationSection } from "@/features/recommendations/section";
import styles from "./catalog.module.css";
export function BookDetail({ id }: { id: string }) {
  const result = useQuery(bookDetailQuery(id));
  const transition = useBookTransition();
  const heading = useRef<HTMLHeadingElement>(null);
  const cover = useRef<HTMLImageElement>(null);
  useLayoutEffect(() => {
    if (heading.current)
      transition?.detailMounted(id, heading.current, !result.isPending);
  }, [id, result.isPending, transition]);
  const book = result.data;
  const { user } = useAuth();
  const viewed = useRef("");
  useEffect(() => {
    if (!book || user?.role !== "READER") return;
    const key = `${user.id}:${book.id}`;
    if (viewed.current === key) return;
    viewed.current = key;
    const event_id = crypto.randomUUID();
    void apiMutation<void>(`/books/${book.id}/views`, "POST", {
      event_id,
    }).catch(() => {
      // Analytics failure must not prevent reading public catalog information.
      viewed.current = "";
    });
  }, [book, user]);
  return (
    <CatalogShell title={book?.title ?? t.details} titleRef={heading}>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        book && (
          <div className={styles.detail}>
            <Cover book={book} imageRef={cover} />
            <div>
              <p className={styles.byline}>
                {book.authors.map((a) => a.full_name).join(", ") || t.none}
              </p>
              <div className={styles.stock}>
                <p className="font-semibold">
                  {t.available}: {book.available_copies} / {book.total_copies}
                </p>
                <p className="mt-2 text-sm">{t.physical}</p>
                <ReserveButton
                  bookId={book.id}
                  available={book.available_copies}
                />
                <FavoriteButton
                  bookId={book.id}
                  coverUrl={book.cover_url}
                  sourceRef={cover}
                />
                <p className="mt-2 text-sm">
                  {t.shelves}: {book.shelf_locations.join(", ") || t.none}
                </p>
              </div>
              <p className="whitespace-pre-wrap leading-relaxed">
                {book.description || t.noDescription}
              </p>
              <dl className={styles.metadata}>
                {[
                  [t.isbn, book.isbn],
                  [t.publisher, book.publisher?.name],
                  [t.year, book.publication_year],
                  [t.language, book.language],
                  [t.pages, book.page_count],
                  [t.categories, book.categories.map((c) => c.name).join(", ")],
                ].map(([key, value]) => (
                  <div key={key}>
                    <dt className="text-sm opacity-70">{key}</dt>
                    <dd className="mt-1">{value || t.none}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        )
      )}
      {book && <RecommendationSection kind="similar" bookId={book.id} />}
    </CatalogShell>
  );
}
