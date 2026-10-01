"use client";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { useAuth } from "@/features/auth/auth-provider";
import { apiMutation } from "@/services/api-client";
import { Cover } from "@/components/books/book-card";
import { catalog as t } from "@/locales/catalog";
import { catalogApi } from "./api";
import { CatalogShell, Failure } from "./shared";
import { ReserveButton } from "@/features/reservations/reserve-button";
import { FavoriteButton } from "@/features/reader/favorites";
import { RecommendationSection } from "@/features/recommendations/section";
export function BookDetail({ id }: { id: string }) {
  const result = useQuery({
    queryKey: ["catalog", "book", id],
    queryFn: () => catalogApi.book(id),
  });
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
    <CatalogShell title={book?.title ?? t.details}>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        book && (
          <div className="grid gap-10 md:grid-cols-[260px_1fr]">
            <Cover book={book} />
            <div>
              <p className="text-lg">
                {book.authors.map((a) => a.full_name).join(", ") || t.none}
              </p>
              <div className="my-6 rounded-xl border bg-white p-5">
                <p className="font-semibold">
                  {t.available}: {book.available_copies} / {book.total_copies}
                </p>
                <p className="mt-2 text-sm">{t.physical}</p>
                <ReserveButton
                  bookId={book.id}
                  available={book.available_copies}
                />
                <FavoriteButton bookId={book.id} />
                <p className="mt-2 text-sm">
                  {t.shelves}: {book.shelf_locations.join(", ") || t.none}
                </p>
              </div>
              <p className="whitespace-pre-wrap leading-relaxed">
                {book.description || t.noDescription}
              </p>
              <dl className="mt-8 grid gap-5 sm:grid-cols-2">
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
