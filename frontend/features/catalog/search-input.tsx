"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { catalog as t } from "@/locales/catalog";
import { searchText as s } from "@/locales/search";
import { searchApi } from "./search-api";
import { Failure, inputClass } from "./shared";
export function SearchInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const [debounced, setDebounced] = useState(value),
    [focused, setFocused] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value.trim()), 250);
    return () => clearTimeout(timer);
  }, [value]);
  const result = useQuery({
    queryKey: ["search", "autocomplete", debounced],
    queryFn: ({ signal }) => searchApi.autocomplete(debounced, signal),
    enabled: focused && debounced.length >= 2,
    staleTime: 30000,
  });
  return (
    <div
      className="relative flex min-w-0 grow gap-2"
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setFocused(false);
      }}
    >
      <label className="min-w-0 grow">
        <span className="sr-only">{s.placeholder}</span>
        <input
          type="search"
          className={inputClass}
          placeholder={s.placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          maxLength={500}
        />
      </label>
      <Button type="submit">{t.find}</Button>
      {focused && debounced.length >= 2 && (
        <div className="absolute top-full right-0 left-0 z-20 mt-2 rounded-lg border bg-white p-3 shadow-lg">
          {result.isPending ? (
            <p role="status">{t.loading}</p>
          ) : result.isError ? (
            <Failure error={result.error} retry={() => void result.refetch()} />
          ) : (
            <ul aria-label={s.suggestions} className="grid gap-1">
              {result.data.items.map((item) => (
                <li key={`${item.kind}:${item.id}`}>
                  <Link
                    className="block rounded px-2 py-2 hover:bg-primary/10"
                    href={
                      item.kind === "book"
                        ? `/books/${item.id}`
                        : `/catalog?${new URLSearchParams({ q: item.label })}`
                    }
                    onClick={() => setFocused(false)}
                  >
                    {item.label}
                    <span className="ml-2 text-xs opacity-60">
                      {item.kind === "book" ? t.books : t.authors}
                    </span>
                  </Link>
                </li>
              ))}
              {!result.data.items.length && (
                <li className="p-2">{t.noResults}</li>
              )}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
