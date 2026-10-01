"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Failure, Field, inputClass } from "@/features/catalog/shared";
import { circulation as t } from "@/locales/circulation";
import { circulationApi, type ReaderOption } from "./api";

export function ReaderPicker({
  value,
  onChange,
  disabled,
}: {
  value: ReaderOption | null;
  onChange: (value: ReaderOption | null) => void;
  disabled: boolean;
}) {
  const [draft, setDraft] = useState(""),
    [q, setQ] = useState("");
  const result = useQuery({
    queryKey: ["readers", "picker", q],
    queryFn: () => circulationApi.readers(q),
    enabled: q.length >= 2,
  });
  return (
    <div className="my-6 max-w-xl space-y-3">
      <Field label={t.readerSearch}>
        <input
          className={inputClass}
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            onChange(null);
            setQ("");
          }}
          disabled={disabled}
          maxLength={500}
        />
      </Field>
      <Button
        type="button"
        variant="outline"
        disabled={disabled || draft.trim().length < 2}
        onClick={() => setQ(draft.trim())}
      >
        {t.findReader}
      </Button>
      {q &&
        (result.isPending ? (
          <p role="status">{t.pending}</p>
        ) : result.isError ? (
          <Failure error={result.error} retry={() => void result.refetch()} />
        ) : (
          <div role="group" aria-label={t.selectReader} className="grid gap-2">
            {result.data.items.length === 0 && <p>{t.noReaders}</p>}
            {result.data.items.map((reader) => (
              <button
                type="button"
                key={reader.id}
                disabled={disabled || reader.status !== "ACTIVE"}
                aria-pressed={value?.id === reader.id}
                onClick={() => onChange(reader)}
                className={`rounded-lg border p-3 text-left disabled:opacity-50 ${value?.id === reader.id ? "border-primary bg-primary/5" : "bg-white"}`}
              >
                <strong>
                  {reader.first_name} {reader.last_name}
                </strong>
                <span className="block text-sm">
                  {reader.email}
                  {reader.status !== "ACTIVE" && ` · ${t.inactive}`}
                </span>
              </button>
            ))}
          </div>
        ))}
    </div>
  );
}
