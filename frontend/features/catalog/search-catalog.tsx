"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { BookCard } from "@/components/books/book-card";
import { useAuth } from "@/features/auth/auth-provider";
import { catalog as t } from "@/locales/catalog";
import { searchText as s } from "@/locales/search";
import { searchApi } from "./search-api";
import { SearchInput } from "./search-input";
import { SearchFilters } from "./search-filters";
import { CatalogShell, Failure, inputClass, Pager } from "./shared";

export function SearchCatalog() {
  const params = useSearchParams();
  return <SearchCatalogBody key={params.get("q") ?? ""} />;
}
function SearchCatalogBody() {
  const searchParams = useSearchParams(),
    router = useRouter(),
    { user } = useAuth();
  const serialized = searchParams.toString();
  const [draft, setDraft] = useState(searchParams.get("q") ?? ""),
    [filters, setFilters] = useState(false);
  const result = useQuery({
    queryKey: ["catalog", "search", serialized, user?.id ?? null],
    queryFn: () => searchApi.search(new URLSearchParams(serialized)),
    refetchOnWindowFocus: false,
  });
  const navigate = (params: URLSearchParams) =>
    router.push(`/catalog?${params}`);
  return (
    <CatalogShell title={t.title}>
      <form
        className="mb-4 flex"
        onSubmit={(e) => {
          e.preventDefault();
          const params = new URLSearchParams(serialized);
          params.set("q", draft.trim());
          params.delete("page");
          navigate(params);
        }}
      >
        <SearchInput value={draft} onChange={setDraft} />
      </form>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <label className="flex items-center gap-3 text-sm">
          {s.mode}
          <select
            className={inputClass}
            value={searchParams.get("mode") ?? "standard"}
            onChange={(e) => {
              const params = new URLSearchParams(serialized);
              params.set("mode", e.target.value);
              params.delete("page");
              navigate(params);
            }}
          >
            {Object.entries(s.modes).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <Button
          variant="outline"
          aria-expanded={filters}
          onClick={() => setFilters(!filters)}
        >
          {filters ? s.hideFilters : s.selectFilters}
        </Button>
        <label className="flex items-center gap-3 text-sm">
          {s.sort}
          <select
            className={inputClass}
            value={searchParams.get("sort") ?? "relevance"}
            onChange={(e) => {
              const params = new URLSearchParams(serialized);
              params.set("sort", e.target.value);
              params.delete("page");
              navigate(params);
            }}
          >
            {Object.entries(s.sorts).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {filters && (
        <SearchFilters
          key={serialized}
          params={new URLSearchParams(serialized)}
          onApply={navigate}
        />
      )}
      {searchParams.get("mode") && searchParams.get("mode") !== "standard" && (
        <p className="mb-5 text-sm text-muted-foreground">{s.semanticHint}</p>
      )}
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {result.data.indexing_pending && (
            <p role="status" className="mb-4 rounded-xl bg-amber-50 p-4">
              {s.indexing}
            </p>
          )}
          <p className="mb-5 text-sm" role="status">
            {s.results}: {result.data.total}
          </p>
          {result.data.items.length ? (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {result.data.items.map((book) => (
                <BookCard
                  key={book.id}
                  book={book}
                  onOpen={() => {
                    if (user?.role === "READER" && result.data.search_event_id)
                      void searchApi
                        .click(result.data.search_event_id, book.id)
                        .catch(() => undefined);
                  }}
                />
              ))}
            </div>
          ) : (
            <p className="rounded-xl border p-10 text-center">{t.empty}</p>
          )}
          <Pager
            page={result.data.page}
            pages={result.data.pages}
            onChange={(page) => {
              const params = new URLSearchParams(serialized);
              params.set("page", String(page));
              navigate(params);
            }}
          />
        </>
      )}
    </CatalogShell>
  );
}
