"use client";
import Image from "next/image";
import Link from "next/link";
import { BookOpen, Library } from "lucide-react";
import { type Ref, useRef, useState } from "react";
import type { Book } from "@/features/catalog/api";
import { catalog as t } from "@/locales/catalog";
import { useBookTransition } from "./book-transition-provider";
import { useBookHover } from "./use-book-hover";
import styles from "./book-card.module.css";

export function Cover({
  book,
  imageRef,
}: {
  book: Book;
  imageRef?: Ref<HTMLImageElement>;
}) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  return (
    <div
      className={styles.cover}
      data-tone={book.id.charCodeAt(book.id.length - 1) % 4}
    >
      {book.cover_url && book.cover_url !== failedUrl ? (
        <Image
          ref={imageRef}
          src={book.cover_url}
          alt={book.title}
          data-book-cover-image=""
          onError={() => setFailedUrl(book.cover_url ?? null)}
          fill
          className={styles.image}
          unoptimized
          sizes="(max-width: 640px) 50vw, 250px"
        />
      ) : (
        <div
          data-book-cover-jacket=""
          className={styles.jacket}
          role="img"
          aria-label={t.noCover}
        >
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
  animateOpen = false,
  animateHover = false,
}: {
  book: Book;
  staffRoot?: string;
  onOpen?: () => void;
  animateOpen?: boolean;
  animateHover?: boolean;
}) {
  const link = useRef<HTMLAnchorElement>(null);
  const transition = useBookTransition();
  const hoverEnabled = animateHover && !staffRoot;
  const { handlers, reset } = useBookHover(hoverEnabled, book);
  const href = staffRoot
    ? `${staffRoot}/books/${book.id}`
    : `/books/${book.id}`;
  return (
    <article
      className={
        hoverEnabled ? `${styles.card} ${styles.tiltable}` : styles.card
      }
      {...handlers}
    >
      <Link
        ref={link}
        aria-label={book.title}
        onClick={onOpen}
        href={href}
        onNavigate={(event) => {
          const anchor = link.current;
          if (!animateOpen || staffRoot || !anchor || !transition) return;
          if (hoverEnabled) {
            reset();
            anchor.dataset.measuringCover = "";
          }
          try {
            if (transition.open(book, anchor, href)) event.preventDefault();
          } finally {
            if (hoverEnabled) delete anchor.dataset.measuringCover;
          }
        }}
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
