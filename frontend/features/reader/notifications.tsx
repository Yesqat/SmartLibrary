"use client";
import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { CatalogShell, Failure, Pager } from "@/features/catalog/shared";
import { reader as t } from "@/locales/reader";
import { notificationLink, readerApi, readerDate } from "./api";
export function Notifications() {
  const [page, setPage] = useState(1),
    [unread, setUnread] = useState(false);
  const cache = useQueryClient();
  const result = useQuery({
    queryKey: ["notifications", page, unread],
    queryFn: () => readerApi.notifications(page, unread),
    refetchInterval: 30000,
  });
  const mutation = useMutation({
    mutationFn: async (id: string | null) => {
      if (id) await readerApi.read(id);
      else await readerApi.readAll();
    },
    onSuccess: async () => {
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["notifications"] }),
        cache.invalidateQueries({ queryKey: ["reader-summary"] }),
      ]);
    },
  });
  return (
    <CatalogShell title={t.notifications}>
      <div className="mb-6 flex flex-wrap items-center gap-5">
        <label className="flex gap-2">
          <input
            type="checkbox"
            checked={unread}
            onChange={(e) => {
              setUnread(e.target.checked);
              setPage(1);
            }}
          />
          {t.unread}
        </label>
        <Button
          variant="outline"
          disabled={mutation.isPending || !result.data?.total}
          onClick={() => mutation.mutate(null)}
        >
          {t.readAll}
        </Button>
      </div>
      {mutation.isError && <Failure error={mutation.error} />}
      {mutation.isSuccess && <p role="status">{t.readDone}</p>}
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {!result.data.total && <p>{t.empty}</p>}
          <ul className="space-y-4">
            {result.data.items.map((row) => (
              <li
                key={row.id}
                className={`rounded-xl border p-5 ${row.is_read ? "bg-white" : "border-primary/40 bg-emerald-50"}`}
              >
                <h2 className="text-lg font-semibold">{row.title}</h2>
                <p className="my-2">{row.message}</p>
                <time className="text-sm" dateTime={row.created_at}>
                  {readerDate(row.created_at)}
                </time>
                <div className="mt-4 flex gap-4">
                  <Link
                    className="text-primary underline"
                    href={notificationLink(row)}
                  >
                    {t.open}
                  </Link>
                  {!row.is_read && (
                    <Button
                      variant="outline"
                      disabled={mutation.isPending}
                      onClick={() => mutation.mutate(row.id)}
                    >
                      {t.read}
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <Pager page={page} pages={result.data.pages} onChange={setPage} />
        </>
      )}
    </CatalogShell>
  );
}
