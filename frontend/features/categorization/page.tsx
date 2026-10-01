"use client";
import Link from "next/link";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  CatalogShell,
  Failure,
  Field,
  inputClass,
  Pager,
} from "@/features/catalog/shared";
import { catalogApi } from "@/features/catalog/api";
import { categorization as t } from "@/locales/categorization";
import { categorizationApi } from "./api";
import { PredictionReview } from "./review";

export function CategorizationPage({ root }: { root: string }) {
  const params = useSearchParams();
  const bookId = params.get("book_id") ?? "";
  const [page, setPage] = useState(1),
    [status, setStatus] = useState("");
  const [method, setMethod] = useState<"classical" | "embedding">("embedding");
  const cache = useQueryClient();
  const book = useQuery({
    queryKey: ["catalog", "book", bookId],
    queryFn: () => catalogApi.book(bookId),
    enabled: !!bookId,
  });
  const list = useQuery({
    queryKey: ["category-predictions", bookId, status, page],
    queryFn: () => categorizationApi.list(page, bookId, status),
  });
  const generate = useMutation({
    mutationFn: () => categorizationApi.generate(bookId, method),
    onSuccess: async () => {
      setPage(1);
      setStatus("");
      await cache.invalidateQueries({ queryKey: ["category-predictions"] });
    },
  });
  return (
    <CatalogShell title={t.predictions}>
      <p>{t.instruction}</p>
      <p className="my-3 text-amber-900">{t.limitation}</p>
      {bookId ? (
        <section className="my-6 rounded-xl border p-5">
          {book.isPending ? (
            <p role="status">{t.loading}</p>
          ) : book.isError ? (
            <Failure error={book.error} retry={() => void book.refetch()} />
          ) : (
            <>
              <Link
                href={`${root}/books/${bookId}`}
                className="font-semibold text-primary underline"
              >
                {book.data.title}
              </Link>
              <p className="my-3 text-sm">{t.savedInput}</p>
              <div className="flex flex-wrap items-end gap-4">
                <Field label={t.method}>
                  <select
                    className={inputClass}
                    value={method}
                    onChange={(event) =>
                      setMethod(event.target.value as typeof method)
                    }
                    disabled={generate.isPending}
                  >
                    <option value="embedding">{t.embedding}</option>
                    <option value="classical">{t.classical}</option>
                  </select>
                </Field>
                <Button
                  disabled={generate.isPending}
                  onClick={() => generate.mutate()}
                >
                  {generate.isPending ? t.working : t.generate}
                </Button>
              </div>
            </>
          )}
          {generate.isError && (
            <Failure error={generate.error} retry={() => generate.mutate()} />
          )}
        </section>
      ) : (
        <p className="my-6">
          {t.choose}{" "}
          <Link href={`${root}/books`} className="text-primary underline">
            Кітаптар
          </Link>
        </p>
      )}
      <div className="my-5 max-w-xs">
        <Field label={t.status}>
          <select
            className={inputClass}
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            <option value="">{t.all}</option>
            {Object.entries(t.states).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
      </div>
      {list.isPending ? (
        <p role="status">{t.loading}</p>
      ) : list.isError ? (
        <Failure error={list.error} retry={() => void list.refetch()} />
      ) : (
        <>
          {!list.data.total && <p>{t.empty}</p>}
          <div className="grid gap-5">
            {list.data.items.map((run) => (
              <PredictionReview
                key={`${run.id}:${run.review_status}`}
                run={run}
              />
            ))}
          </div>
          <Pager page={page} pages={list.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
