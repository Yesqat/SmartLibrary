"use client";
import Link from "next/link";
import { BookCard } from "@/components/books/book-card";
import { assistant as t } from "@/locales/assistant";
import { readerDate } from "@/features/reader/api";
import type { Message } from "./api";
export function MessageView({ message }: { message: Message }) {
  return (
    <article
      className={`rounded-xl border p-5 ${message.role === "USER" ? "bg-emerald-50" : "bg-white"}`}
      aria-label={message.role === "USER" ? t.you : t.bot}
    >
      <p className="mb-2 font-semibold">
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
          <div className="grid gap-4 sm:grid-cols-2">
            {message.books.map((book) => (
              <div key={book.id}>
                <BookCard book={book} />
                <Link
                  href={`/books/${book.id}`}
                  className="mt-3 inline-block text-primary underline"
                >
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
