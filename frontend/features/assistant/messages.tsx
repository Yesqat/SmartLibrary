"use client";
import Link from "next/link";
import { BookOpen, MessagesSquare, UserRound } from "lucide-react";
import { BookCard } from "@/components/books/book-card";
import { assistant as t } from "@/locales/assistant";
import { readerDate } from "@/features/reader/api";
import type { Message } from "./api";
import styles from "./assistant.module.css";
export function MessageView({ message }: { message: Message }) {
  const SpeakerIcon = message.role === "USER" ? UserRound : MessagesSquare;
  return (
    <article
      className={`rounded-xl border p-5 ${message.role === "USER" ? "bg-indigo-50" : "bg-white"}`}
      aria-label={message.role === "USER" ? t.you : t.bot}
    >
      <p className={styles.speaker}>
        <SpeakerIcon aria-hidden="true" />
        {message.role === "USER" ? t.you : t.bot}
      </p>
      <p
        className="whitespace-pre-wrap break-words"
        role={message.error_code ? "alert" : undefined}
      >
        {message.error_code ? t.unavailable : message.content}
      </p>
      <p className="mt-3 text-xs text-muted-foreground">
        {t.observed}:{" "}
        <time dateTime={message.created_at}>
          {readerDate(message.created_at)}
        </time>
      </p>
      {message.books.length > 0 && (
        <>
          <p className="my-4 text-sm">{t.confirmation}</p>
          <div className={styles.recommendedBooks}>
            {message.books.map((book) => (
              <div key={book.id} className={styles.recommendedBook}>
                <BookCard book={book} />
                <Link href={`/books/${book.id}`} className={styles.bookLink}>
                  <BookOpen aria-hidden="true" />
                  {t.reserve}
                </Link>
              </div>
            ))}
          </div>
        </>
      )}
    </article>
  );
}
