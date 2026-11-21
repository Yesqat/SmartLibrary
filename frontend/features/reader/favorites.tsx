"use client";
import { useState } from "react";
import { Heart } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { BookCard } from "@/components/books/book-card";
import { CatalogShell, Failure, Pager } from "@/features/catalog/shared";
import { useAuth } from "@/features/auth/auth-provider";
import { reader as t } from "@/locales/reader";
import { readerApi } from "./api";

export function FavoriteButton({
  bookId,
  initial,
}: {
  bookId: string;
  initial?: boolean;
}) {
  const { user } = useAuth();
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ["favorites", "state", bookId],
    queryFn: () => readerApi.favorite(bookId),
    enabled: user?.role === "READER",
    initialData: initial === undefined ? undefined : { is_favorite: initial },
  });
  const mutation = useMutation({
    mutationFn: (enabled: boolean) => readerApi.setFavorite(bookId, enabled),
    onSuccess: async () => {
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["favorites"] }),
        cache.invalidateQueries({ queryKey: ["recommendations"] }),
        cache.invalidateQueries({ queryKey: ["reader-summary"] }),
      ]);
    },
  });
  if (user?.role !== "READER") return null;
  return (
    <div className="mt-4">
      <Button
        variant="outline"
        disabled={query.isPending || query.isError || mutation.isPending}
        aria-pressed={query.data?.is_favorite ?? false}
        onClick={() => mutation.mutate(!query.data?.is_favorite)}
      >
        <Heart
          size={16}
          aria-hidden="true"
          fill={query.data?.is_favorite ? "currentColor" : "none"}
        />
        {query.data?.is_favorite ? t.removeFavorite : t.addFavorite}
      </Button>
      {query.isError && (
        <Failure error={query.error} retry={() => void query.refetch()} />
      )}
      {mutation.isError && <Failure error={mutation.error} />}
      {mutation.isSuccess && (
        <p role="status" className="mt-2 text-sm">
          {mutation.variables ? t.favoriteAdded : t.favoriteRemoved}
        </p>
      )}
    </div>
  );
}
export function Favorites() {
  const [page, setPage] = useState(1);
  const result = useQuery({
    queryKey: ["favorites", "list", page],
    queryFn: () => readerApi.favorites(page),
  });
  return (
    <CatalogShell title={t.favorites}>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {!result.data.total && <p>{t.empty}</p>}
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {result.data.items.map((book) => (
              <div key={book.id}>
                <BookCard book={book} />
                <FavoriteButton bookId={book.id} initial />
              </div>
            ))}
          </div>
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
