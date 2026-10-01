"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  CatalogShell,
  Failure,
  Field,
  inputClass,
  Pager,
} from "@/features/catalog/shared";
import { librarian as t } from "@/locales/librarian";
import { librarianApi } from "./api";
export function Readers() {
  const [q, setQ] = useState(""),
    [draft, setDraft] = useState(""),
    [page, setPage] = useState(1),
    [status, setStatus] = useState("");
  const result = useQuery({
    queryKey: ["readers", page, q, status],
    queryFn: () => librarianApi.readers(page, q, status),
  });
  return (
    <CatalogShell title={t.readers}>
      <form
        className="mb-6 flex flex-wrap items-end gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          setQ(draft);
          setPage(1);
        }}
      >
        <Field label={t.search}>
          <input
            className={inputClass}
            maxLength={500}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
        </Field>
        <Field label={t.status}>
          <select
            className={inputClass}
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">{t.all}</option>
            {Object.entries(t.states).map(([key, value]) => (
              <option key={key} value={key}>
                {value}
              </option>
            ))}
          </select>
        </Field>
        <Button>{t.find}</Button>
      </form>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {!result.data.total && <p>{t.empty}</p>}
          <ul className="grid gap-4 md:grid-cols-2">
            {result.data.items.map((row) => (
              <li key={row.id} className="rounded-xl border bg-white p-5">
                <Link
                  href={`/librarian/readers/${row.id}`}
                  className="text-lg font-semibold text-primary underline"
                >
                  {row.first_name} {row.last_name}
                </Link>
                <p>{row.email}</p>
                <p>{t.states[row.status]}</p>
              </li>
            ))}
          </ul>
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
