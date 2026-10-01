"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { catalog as t } from "@/locales/catalog";
import { apiMutation } from "@/services/api-client";
import { catalogApi, type Copy, type CopyInput, type CopyPatch } from "./api";
import { CatalogShell, Failure, Field, inputClass, Pager } from "./shared";
export function CopyManager({ id }: { id: string }) {
  const [page, setPage] = useState(1),
    [editing, setEditing] = useState<Copy | null | undefined>(undefined);
  const cache = useQueryClient();
  const book = useQuery({
    queryKey: ["catalog", "book", id, "staff"],
    queryFn: () => catalogApi.book(id, true),
  });
  const result = useQuery({
    queryKey: ["catalog", "copies", id, page],
    queryFn: () => catalogApi.copies(id, page),
  });
  const save = useMutation({
    mutationFn: ({
      path,
      data,
      method,
    }: {
      path: string;
      data: CopyInput | CopyPatch | { archived: boolean };
      method: "POST" | "PATCH";
    }) => apiMutation<Copy>(path, method, data),
    onSuccess: async () => {
      setEditing(undefined);
      await cache.invalidateQueries({ queryKey: ["catalog"] });
      await cache.invalidateQueries({ queryKey: ["search"] });
      await cache.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });
  return (
    <CatalogShell
      title={`${t.copies}${book.data ? " · " + book.data.title : ""}`}
    >
      <p className="mb-5 text-sm">{t.metadataOnly}</p>
      <Button
        onClick={() => {
          setEditing(null);
          save.reset();
        }}
        disabled={!!book.data?.archived_at}
      >
        {t.addCopy}
      </Button>
      {editing !== undefined && (
        <form
          key={editing?.id ?? "new"}
          className="my-6 grid gap-4 rounded-xl border bg-white p-6 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            const value = (name: string) => String(form.get(name) ?? "");
            const status = value("status") as Copy["status"];
            if (
              editing &&
              status !== editing.status &&
              !window.confirm(t.confirmState)
            )
              return;
            const data: CopyPatch = {
              inventory_number: value("inventory"),
              shelf_location: value("shelf") || null,
              condition: value("condition") as Copy["condition"],
              acquired_at: value("acquired") || null,
              ...(editing ? { status } : {}),
            };
            save.mutate({
              path: editing ? `/copies/${editing.id}` : `/books/${id}/copies`,
              method: editing ? "PATCH" : "POST",
              data,
            });
          }}
        >
          <Field label={t.inventory}>
            <input
              className={inputClass}
              name="inventory"
              required
              maxLength={100}
              defaultValue={editing?.inventory_number}
            />
          </Field>
          <Field label={t.shelf}>
            <input
              className={inputClass}
              name="shelf"
              maxLength={150}
              defaultValue={editing?.shelf_location ?? ""}
            />
          </Field>
          <Field label={t.condition}>
            <select
              className={inputClass}
              name="condition"
              defaultValue={editing?.condition ?? "GOOD"}
            >
              {Object.entries(t.conditions).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          {editing && (
            <Field label={t.status}>
              <select
                className={inputClass}
                name="status"
                defaultValue={editing.status}
              >
                {Object.entries(t.statuses).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label={t.acquired}>
            <input
              type="date"
              name="acquired"
              className={inputClass}
              defaultValue={editing?.acquired_at ?? ""}
            />
          </Field>
          <div className="flex items-end gap-3">
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? t.loading : t.save}
            </Button>
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
      {save.isSuccess && (
        <p role="status" className="mt-4">
          {t.saved}
        </p>
      )}
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          <div className="mt-6 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{t.copies}</caption>
              <thead>
                <tr>
                  {[t.inventory, t.shelf, t.condition, t.status, t.edit].map(
                    (label) => (
                      <th key={label} className="border-b p-3">
                        {label}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {result.data.items.map((copy) => (
                  <tr key={copy.id} className="border-b">
                    <td className="p-3">{copy.inventory_number}</td>
                    <td className="p-3">{copy.shelf_location || t.none}</td>
                    <td className="p-3">{t.conditions[copy.condition]}</td>
                    <td className="p-3">
                      {copy.archived_at ? t.archived : t.statuses[copy.status]}
                    </td>
                    <td className="flex gap-2 p-3">
                      <Button
                        variant="outline"
                        disabled={
                          !!copy.archived_at ||
                          save.isPending ||
                          ["RESERVED", "BORROWED"].includes(copy.status)
                        }
                        onClick={() => {
                          setEditing(copy);
                          save.reset();
                        }}
                      >
                        {t.edit}
                      </Button>
                      <Button
                        variant="outline"
                        disabled={save.isPending}
                        onClick={() => {
                          if (
                            copy.archived_at ||
                            window.confirm(t.confirmArchive)
                          )
                            save.mutate({
                              path: `/copies/${copy.id}/archive`,
                              method: "PATCH",
                              data: { archived: !copy.archived_at },
                            });
                        }}
                      >
                        {copy.archived_at ? t.restore : t.archive}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!result.data.total && <p className="py-6">{t.empty}</p>}
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
