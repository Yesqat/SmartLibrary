"use client";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { catalog as t } from "@/locales/catalog";
import { catalogApi, label, type Reference, type ReferenceKind } from "./api";
import { Failure, inputClass, Pager } from "./shared";
export function ReferencePicker({
  kind,
  selected,
  onChange,
  single = false,
}: {
  kind: ReferenceKind;
  selected: Reference[];
  onChange: (items: Reference[]) => void;
  single?: boolean;
}) {
  const [input, setInput] = useState(""),
    [q, setQ] = useState(""),
    [page, setPage] = useState(1),
    [open, setOpen] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(input.trim());
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [input]);
  const result = useQuery({
    queryKey: ["catalog", "references", kind, q, page],
    queryFn: () => catalogApi.references(kind, q, page),
    enabled: open,
  });
  return (
    <fieldset className="rounded-lg border p-4">
      <legend className="px-2 text-sm font-medium">{t[kind]}</legend>
      <div className="mb-3 flex flex-wrap gap-2">
        {selected.map((item) => (
          <Button
            key={item.id}
            variant="outline"
            type="button"
            onClick={() =>
              onChange(selected.filter((row) => row.id !== item.id))
            }
            aria-label={`${t.cancel}: ${label(item)}`}
          >
            {label(item)} ×
          </Button>
        ))}
      </div>
      <Button
        variant="outline"
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {open ? t.close : t.select}
      </Button>
      {open && (
        <div className="mt-4">
          <label className="grid gap-2 text-sm">
            {t.find}: {t[kind]}
            <input
              className={inputClass}
              maxLength={500}
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
          </label>
          {result.isPending ? (
            <p role="status">{t.loading}</p>
          ) : result.isError ? (
            <Failure error={result.error} retry={() => void result.refetch()} />
          ) : (
            <>
              <ul className="mt-3 grid gap-2">
                {result.data.items.map((item) => (
                  <li key={item.id}>
                    <Button
                      variant="outline"
                      type="button"
                      disabled={selected.some((row) => row.id === item.id)}
                      onClick={() => {
                        onChange(single ? [item] : [...selected, item]);
                        if (single) setOpen(false);
                      }}
                    >
                      {label(item)}
                    </Button>
                  </li>
                ))}
              </ul>
              {!result.data.total && <p>{t.noResults}</p>}
              <Pager page={page} pages={result.data.pages} onChange={setPage} />
            </>
          )}
        </div>
      )}
    </fieldset>
  );
}
