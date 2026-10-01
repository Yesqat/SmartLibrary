"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { CatalogShell, Failure, Pager } from "@/features/catalog/shared";
import { assistant as t } from "@/locales/assistant";
import { assistantApi } from "./api";
import { Chat } from "./chat";
export function AssistantPage() {
  const [id, setId] = useState("");
  const [page, setPage] = useState(1);
  const cache = useQueryClient();
  const list = useQuery({
    queryKey: ["assistant-list", page],
    queryFn: () => assistantApi.list(page),
  });
  const create = useMutation({
    mutationFn: assistantApi.create,
    onSuccess: async (row) => {
      setId(row.id);
      setPage(1);
      await cache.invalidateQueries({ queryKey: ["assistant-list"] });
    },
  });
  return (
    <CatalogShell title={t.title}>
      <p className="mb-6 rounded-xl bg-emerald-50 p-4 text-sm">{t.privacy}</p>
      <div className="grid gap-7 md:grid-cols-[220px_minmax(0,1fr)]">
        <aside aria-label={t.chats} className="space-y-4">
          <Button disabled={create.isPending} onClick={() => create.mutate()}>
            {t.newChat}
          </Button>
          {create.isError && <Failure error={create.error} />}
          {list.isPending ? (
            <p role="status">{t.loading}</p>
          ) : list.isError ? (
            <Failure error={list.error} retry={() => void list.refetch()} />
          ) : (
            <>
              {!list.data.total && <p>{t.noChats}</p>}
              <ul className="space-y-2">
                {list.data.items.map((row) => (
                  <li key={row.id}>
                    <button
                      className={`w-full break-words rounded-lg border p-3 text-left text-sm ${id === row.id ? "bg-emerald-50" : "bg-white"}`}
                      aria-current={id === row.id ? "true" : undefined}
                      onClick={() => setId(row.id)}
                    >
                      {row.title || t.untitled}
                    </button>
                  </li>
                ))}
              </ul>
              {list.data.pages > 1 && (
                <Pager page={page} pages={list.data.pages} onChange={setPage} />
              )}
            </>
          )}
        </aside>
        {id ? (
          <Chat key={id} id={id} />
        ) : (
          <div className="rounded-xl border bg-white p-8">
            <p>{t.empty}</p>
            <p className="mt-3 text-muted-foreground">{t.newChat}</p>
          </div>
        )}
      </div>
    </CatalogShell>
  );
}
