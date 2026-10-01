"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { apiRequest } from "@/services/api-client";
import { catalog as t } from "@/locales/catalog";
import { searchText as s } from "@/locales/search";
import { type Reference, type ReferenceKind } from "./api";
import { ReferencePicker } from "./reference-picker";
import { Failure, Field, inputClass } from "./shared";

const keys = {
  authors: "author",
  categories: "category",
  publishers: "publisher",
} as const;
function ReferenceFilter({
  kind,
  id,
  onChange,
}: {
  kind: ReferenceKind;
  id: string | null;
  onChange: (id: string | null) => void;
}) {
  const cache = useQueryClient();
  const result = useQuery({
    queryKey: ["catalog", "reference", kind, id],
    queryFn: () => apiRequest<Reference>(`/${kind}/${id}`),
    enabled: !!id,
  });
  return (
    <div>
      {id && result.isPending && <p role="status">{t.loading}</p>}
      {result.isError && (
        <Failure error={result.error} retry={() => void result.refetch()} />
      )}
      <ReferencePicker
        kind={kind}
        selected={result.data ? [result.data] : []}
        single
        onChange={(rows) => {
          if (rows[0])
            cache.setQueryData(
              ["catalog", "reference", kind, rows[0].id],
              rows[0],
            );
          onChange(rows[0]?.id ?? null);
        }}
      />
    </div>
  );
}
export function SearchFilters({
  params,
  onApply,
}: {
  params: URLSearchParams;
  onApply: (params: URLSearchParams) => void;
}) {
  const [selected, setSelected] = useState<
    Record<ReferenceKind, string | null>
  >({
    authors: params.get("author"),
    categories: params.get("category"),
    publishers: params.get("publisher"),
  });
  return (
    <form
      className="mb-6 grid gap-4 rounded-xl border bg-white p-5"
      onSubmit={(e) => {
        e.preventDefault();
        const data = new FormData(e.currentTarget);
        const next = new URLSearchParams(params);
        next.delete("page");
        for (const kind of Object.keys(keys) as ReferenceKind[]) {
          const id = selected[kind];
          if (id) next.set(keys[kind], id);
          else next.delete(keys[kind]);
        }
        for (const name of ["available", "year_from", "year_to"]) {
          const value = String(data.get(name) ?? "");
          if (value) next.set(name, value);
          else next.delete(name);
        }
        next.delete("language");
        data
          .getAll("language")
          .forEach((value) => next.append("language", String(value)));
        onApply(next);
      }}
    >
      <div className="grid gap-4 sm:grid-cols-3">
        {(Object.keys(keys) as ReferenceKind[]).map((kind) => (
          <ReferenceFilter
            key={kind}
            kind={kind}
            id={selected[kind]}
            onChange={(id) =>
              setSelected((previous) => ({ ...previous, [kind]: id }))
            }
          />
        ))}
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label={s.availability}>
          <select
            name="available"
            className={inputClass}
            defaultValue={params.get("available") ?? ""}
          >
            <option value="">{s.all}</option>
            <option value="true">{s.available}</option>
            <option value="false">{s.unavailable}</option>
          </select>
        </Field>
        <Field label={s.yearFrom}>
          <input
            name="year_from"
            type="number"
            min={1}
            max={9999}
            className={inputClass}
            defaultValue={params.get("year_from") ?? ""}
          />
        </Field>
        <Field label={s.yearTo}>
          <input
            name="year_to"
            type="number"
            min={1}
            max={9999}
            className={inputClass}
            defaultValue={params.get("year_to") ?? ""}
          />
        </Field>
      </div>
      <fieldset className="flex flex-wrap gap-4">
        <legend className="mb-2 text-sm">{s.language}</legend>
        {Object.entries(s.languages).map(([value, label]) => (
          <label key={value} className="flex items-center gap-2">
            <input
              type="checkbox"
              name="language"
              value={value}
              defaultChecked={params.getAll("language").includes(value)}
            />
            {label}
          </label>
        ))}
      </fieldset>
      <div className="flex gap-3">
        <Button type="submit">{s.apply}</Button>
        <Button
          variant="outline"
          type="button"
          onClick={() =>
            onApply(
              new URLSearchParams(
                params.get("q") ? { q: params.get("q")! } : {},
              ),
            )
          }
        >
          {s.reset}
        </Button>
      </div>
    </form>
  );
}
