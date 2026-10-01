"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { catalog as t } from "@/locales/catalog";
import { apiMutation } from "@/services/api-client";
import { catalogApi, label, type Reference, type ReferenceKind } from "./api";
import { CatalogShell, Failure, Field, inputClass, Pager } from "./shared";
export function ReferenceManager({
  initialKind = "authors",
}: {
  initialKind?: ReferenceKind;
}) {
  const [kind, setKind] = useState<ReferenceKind>(initialKind),
    [q, setQ] = useState(""),
    [page, setPage] = useState(1),
    [archived, setArchived] = useState(false),
    [editing, setEditing] = useState<Reference | null | undefined>(undefined);
  const cache = useQueryClient();
  const result = useQuery({
    queryKey: ["catalog", "references", kind, q, page, archived],
    queryFn: () => catalogApi.references(kind, q, page, archived),
  });
  const save = useMutation({
    mutationFn: ({
      path,
      data,
      method,
    }: {
      path: string;
      data: Record<string, unknown>;
      method: "PATCH" | "POST";
    }) => apiMutation<Reference>(path, method, data),
    onSuccess: async () => {
      setEditing(undefined);
      await cache.invalidateQueries({ queryKey: ["catalog"] });
      await cache.invalidateQueries({ queryKey: ["search"] });
      await cache.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });
  const extra =
    kind === "authors"
      ? "biography"
      : kind === "categories"
        ? "description"
        : "country";
  const extraValue =
    editing && extra in editing
      ? String(editing[extra as keyof typeof editing] ?? "")
      : "";
  return (
    <CatalogShell title={t.references}>
      <div className="flex flex-wrap gap-3">
        {(["authors", "categories", "publishers"] as const).map((value) => (
          <Button
            key={value}
            variant={kind === value ? "default" : "outline"}
            onClick={() => {
              setKind(value);
              setPage(1);
              setQ("");
              setEditing(undefined);
              save.reset();
            }}
          >
            {t[value]}
          </Button>
        ))}
      </div>
      <div className="my-6 flex flex-wrap gap-4">
        <form
          className="flex grow gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setQ(String(new FormData(e.currentTarget).get("q") ?? ""));
            setPage(1);
          }}
        >
          <input
            aria-label={t.find}
            name="q"
            className={inputClass}
            maxLength={500}
          />
          <Button>{t.find}</Button>
        </form>
        <Button
          onClick={() => {
            setEditing(null);
            save.reset();
          }}
        >
          {t.addReference}
        </Button>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={archived}
            onChange={(e) => {
              setArchived(e.target.checked);
              setPage(1);
            }}
          />
          {t.includeArchived}
        </label>
      </div>
      {editing !== undefined && (
        <form
          key={editing?.id ?? kind}
          className="mb-6 grid gap-4 rounded-xl border bg-white p-6"
          onSubmit={(e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            save.mutate({
              path: `/${kind}${editing ? "/" + editing.id : ""}`,
              method: editing ? "PATCH" : "POST",
              data: {
                [kind === "authors" ? "full_name" : "name"]: String(
                  form.get("name"),
                ),
                [extra]: String(form.get("extra")) || null,
              },
            });
          }}
        >
          <Field label={kind === "authors" ? t.fullName : t.name}>
            <input
              className={inputClass}
              name="name"
              required
              maxLength={
                kind === "authors" ? 300 : kind === "categories" ? 150 : 250
              }
              defaultValue={editing ? label(editing) : ""}
            />
          </Field>
          <Field label={t[extra]}>
            <textarea
              className={inputClass}
              name="extra"
              rows={3}
              maxLength={extra === "country" ? 100 : 20000}
              defaultValue={extraValue}
            />
          </Field>
          <div className="flex gap-3">
            <Button disabled={save.isPending}>{t.save}</Button>
            <Button
              type="button"
              variant="outline"
              disabled={save.isPending}
              onClick={() => setEditing(undefined)}
            >
              {t.cancel}
            </Button>
          </div>
        </form>
      )}
      {save.isError && <Failure error={save.error} />}{" "}
      {save.isSuccess && <p role="status">{t.saved}</p>}
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          <ul className="divide-y rounded-xl border bg-white">
            {result.data.items.map((row) => (
              <li
                key={row.id}
                className="flex flex-wrap items-center justify-between gap-4 p-4"
              >
                <span>
                  {label(row)} {row.archived_at && `· ${t.archived}`}
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    disabled={!!row.archived_at || save.isPending}
                    onClick={() => {
                      setEditing(row);
                      save.reset();
                    }}
                  >
                    {t.edit}
                  </Button>
                  <Button
                    variant="outline"
                    disabled={save.isPending}
                    onClick={() => {
                      if (row.archived_at || window.confirm(t.confirmArchive))
                        save.mutate({
                          path: `/${kind}/${row.id}/archive`,
                          method: "PATCH",
                          data: { archived: !row.archived_at },
                        });
                    }}
                  >
                    {row.archived_at ? t.restore : t.archive}
                  </Button>
                </div>
              </li>
            ))}
          </ul>
          {!result.data.total && <p>{t.empty}</p>}
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
