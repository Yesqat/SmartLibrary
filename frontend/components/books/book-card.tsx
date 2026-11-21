import Image from "next/image";
import Link from "next/link";
import { BookOpen, Library } from "lucide-react";
import type { Book } from "@/features/catalog/api";
import { catalog as t } from "@/locales/catalog";
import styles from "./book-card.module.css";

export function Cover({ book }: { book: Book }) {
  return (
    <div
      className={styles.cover}
      data-tone={book.id.charCodeAt(book.id.length - 1) % 4}
    >
      {book.cover_url ? (
        <Image
          src={book.cover_url}
          alt={book.title}
          fill
          className={styles.image}
          unoptimized
          sizes="(max-width: 640px) 50vw, 250px"
        />
      ) : (
        <div className={styles.jacket} role="img" aria-label={t.noCover}>
          <BookOpen aria-hidden="true" />
        </div>
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
    <article className={styles.card}>
      <Link
        aria-label={book.title}
        onClick={onOpen}
        href={staffRoot ? `${staffRoot}/books/${book.id}` : `/books/${book.id}`}
        className={styles.link}
      >
        <Cover book={book} />
        <h2>{book.title}</h2>
      </Link>
      <p className={styles.author}>
        {book.authors.map((a) => a.full_name).join(", ") || t.none}
      </p>
      <p className={styles.availability}>
        <Library aria-hidden="true" />
        {t.available}: {book.available_copies} / {book.total_copies}
      </p>
      <p className={styles.meta}>
        {book.language}
        {book.publication_year ? ` · ${book.publication_year}` : ""}
        {book.categories[0] ? ` · ${book.categories[0].name}` : ""}
      </p>
      {book.archived_at && <p className={styles.archived}>{t.archived}</p>}
    </article>
  );
}
