import Image from "next/image";
import Link from "next/link";
import { BookOpen } from "lucide-react";
import type { Book } from "@/features/catalog/api";
import { catalog as t } from "@/locales/catalog";
export function Cover({ book }: { book: Book }) {
  return (
    <div className="relative flex aspect-[3/4] items-center justify-center overflow-hidden rounded-lg bg-emerald-950/5">
      {book.cover_url ? (
        <Image
          src={book.cover_url}
          alt={book.title}
          fill
          className="object-contain"
          unoptimized
          sizes="(max-width: 640px) 50vw, 250px"
        />
      ) : (
        <BookOpen aria-label={t.noCover} className="size-14 text-primary/40" />
      )}
    </div>
  );
}
export function BookCard({
  book,
  staffRoot,
  onOpen,
}: {
  book: Book;
  staffRoot?: string;
  onOpen?: () => void;
}) {
  return (
    <article className="rounded-xl border bg-white p-4 shadow-sm">
      <Link
        aria-label={book.title}
        onClick={onOpen}
        href={staffRoot ? `${staffRoot}/books/${book.id}` : `/books/${book.id}`}
        className="grid gap-4"
      >
        <Cover book={book} />
        <h2 className="text-lg font-semibold">{book.title}</h2>
      </Link>
      <p className="mt-1 text-sm">
        {book.authors.map((a) => a.full_name).join(", ") || t.none}
      </p>
      <p className="mt-3 text-sm font-medium">
        {t.available}: {book.available_copies} / {book.total_copies}
      </p>
      <p className="mt-2 text-xs opacity-70">
        {book.language}
        {book.publication_year ? ` · ${book.publication_year}` : ""}
        {book.categories[0] ? ` · ${book.categories[0].name}` : ""}
      </p>
      {book.archived_at && (
        <p className="mt-2 text-sm text-amber-800">{t.archived}</p>
      )}
    </article>
  );
}
