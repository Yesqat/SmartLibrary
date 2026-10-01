"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Cover } from "@/components/books/book-card";
import { catalog as t } from "@/locales/catalog";
import { apiMutation } from "@/services/api-client";
import { catalogApi, type Book, type BookInput, type Reference } from "./api";
import { CatalogShell, Failure, Field, inputClass } from "./shared";
import { ReferencePicker } from "./reference-picker";
import { categorization as ct } from "@/locales/categorization";
function BookForm({ book, root }: { book?: Book; root: string }) {
  const [authors, setAuthors] = useState<Reference[]>(book?.authors ?? []),
    [categories, setCategories] = useState<Reference[]>(book?.categories ?? []),
    [publishers, setPublishers] = useState<Reference[]>(
      book?.publisher ? [book.publisher] : [],
    );
  const router = useRouter(),
    cache = useQueryClient();
  const save = useMutation({
    mutationFn: (data: BookInput) => catalogApi.save(data, book?.id),
    onSuccess: async (row) => {
      await cache.invalidateQueries({ queryKey: ["catalog"] });
      await cache.invalidateQueries({ queryKey: ["search"] });
      await cache.invalidateQueries({ queryKey: ["recommendations"] });
      if (!book) router.replace(`${root}/books/${row.id}`);
    },
  });
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const data = new FormData(e.currentTarget);
        const text = (key: string) => String(data.get(key) ?? "").trim();
        const number = (key: string) => (text(key) ? Number(text(key)) : null);
        save.mutate({
          title: text("title"),
          isbn: text("isbn") || null,
          description: text("description") || null,
          language: text("language"),
          publication_year: number("year"),
          page_count: number("pages"),
          author_ids: authors.map((a) => a.id),
          category_ids: categories.map((c) => c.id),
          publisher_id: publishers[0]?.id ?? null,
        });
      }}
      className="grid gap-5"
    >
      <fieldset
        disabled={save.isPending || !!book?.archived_at}
        className="grid gap-5"
      >
        <Field label={t.titleField + " *"}>
          <input
            className={inputClass}
            name="title"
            defaultValue={book?.title}
            maxLength={500}
            required
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t.isbn}>
            <input
              className={inputClass}
              name="isbn"
              defaultValue={book?.isbn ?? ""}
              maxLength={32}
            />
          </Field>
          <Field label={t.language + " *"}>
            <input
              className={inputClass}
              name="language"
              defaultValue={book?.language ?? "kk"}
              maxLength={35}
              pattern="[a-z]{2,3}(-[A-Za-z0-9]{2,8})*"
              required
            />
          </Field>
          <Field label={t.year}>
            <input
              className={inputClass}
              type="number"
              name="year"
              defaultValue={book?.publication_year ?? ""}
              min={1}
              max={9999}
            />
          </Field>
          <Field label={t.pages}>
            <input
              className={inputClass}
              name="pages"
              type="number"
              defaultValue={book?.page_count ?? ""}
              min={1}
              max={100000}
            />
          </Field>
        </div>
        <Field label={t.description}>
          <textarea
            className={inputClass}
            name="description"
            rows={6}
            defaultValue={book?.description ?? ""}
            maxLength={20000}
          />
        </Field>
        <ReferencePicker
          kind="authors"
          selected={authors}
          onChange={setAuthors}
        />
        <ReferencePicker
          kind="categories"
          selected={categories}
          onChange={setCategories}
        />
        <ReferencePicker
          kind="publishers"
          selected={publishers}
          onChange={setPublishers}
          single
        />
        <Button type="submit" className="justify-self-start">
          {save.isPending ? t.loading : t.save}
        </Button>
      </fieldset>
      {save.isError && <Failure error={save.error} />}{" "}
      {save.isSuccess && <p role="status">{t.saved}</p>}
    </form>
  );
}
function CoverEditor({ book }: { book: Book }) {
  const cache = useQueryClient();
  const upload = useMutation({
    mutationFn: (file: File | null) => {
      if (!file) return apiMutation<Book>(`/books/${book.id}/cover`, "DELETE");
      const form = new FormData();
      form.set("file", file);
      return apiMutation<Book>(`/books/${book.id}/cover`, "POST", form);
    },
    onSuccess: () => cache.invalidateQueries({ queryKey: ["catalog"] }),
  });
  return (
    <section className="grid gap-4">
      <h2 className="font-semibold">{t.cover}</h2>
      <Cover book={book} />
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const file = new FormData(e.currentTarget).get("file");
          if (file instanceof File && file.size) upload.mutate(file);
        }}
        className="grid gap-3"
      >
        <label className="grid gap-2 text-sm">
          {t.imageHint}
          <input
            type="file"
            name="file"
            accept="image/jpeg,image/png,image/webp"
            required
            disabled={upload.isPending || !!book.archived_at}
            className="w-full text-sm"
          />
        </label>
        <Button disabled={upload.isPending || !!book.archived_at} type="submit">
          {t.upload}
        </Button>
      </form>
      {book.cover_url && (
        <Button
          variant="outline"
          disabled={upload.isPending || !!book.archived_at}
          onClick={() => {
            if (window.confirm(t.confirmRemove)) upload.mutate(null);
          }}
        >
          {t.removeCover}
        </Button>
      )}
      {upload.isError && <Failure error={upload.error} />}{" "}
      {upload.isSuccess && <p role="status">{t.saved}</p>}
    </section>
  );
}
export function BookEditor({ id, root }: { id?: string; root: string }) {
  const cache = useQueryClient();
  const result = useQuery({
    queryKey: ["catalog", "book", id, "staff"],
    queryFn: () => catalogApi.book(id!, true),
    enabled: !!id,
  });
  const archive = useMutation({
    mutationFn: (value: boolean) =>
      apiMutation<Book>(`/books/${id}/archive`, "PATCH", { archived: value }),
    onSuccess: () => cache.invalidateQueries({ queryKey: ["catalog"] }),
  });
  return (
    <CatalogShell title={id ? t.edit : t.add}>
      {id && result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : id && result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {result.data && (
            <div className="mb-6 flex flex-wrap items-center gap-4">
              <Button asChild variant="outline">
                <Link href={`${root}/books/${id}/copies`}>{t.copies}</Link>
              </Button>
              {!result.data.archived_at && (
                <Button asChild variant="outline">
                  <Link href={`${root}/category-predictions?book_id=${id}`}>
                    {ct.title}
                  </Link>
                </Button>
              )}
              <Button
                variant="outline"
                disabled={archive.isPending}
                onClick={() => {
                  if (
                    result.data?.archived_at ||
                    window.confirm(t.confirmArchive)
                  )
                    archive.mutate(!result.data?.archived_at);
                }}
              >
                {result.data.archived_at ? t.restore : t.archive}
              </Button>
              {result.data.archived_at && <span>{t.archived}</span>}
            </div>
          )}
          {archive.isError && <Failure error={archive.error} />}
          <div className="grid gap-10 md:grid-cols-[1fr_240px]">
            <BookForm key={id ?? "new"} book={result.data} root={root} />
            {result.data && <CoverEditor book={result.data} />}
          </div>
        </>
      )}
    </CatalogShell>
  );
}
