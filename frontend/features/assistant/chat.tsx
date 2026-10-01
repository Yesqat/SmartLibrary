"use client";
import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Failure, Pager, inputClass } from "@/features/catalog/shared";
import { ApiError } from "@/services/api-client";
import { assistant as t } from "@/locales/assistant";
import { assistantApi } from "./api";
import { MessageView } from "./messages";
export function Chat({ id }: { id: string }) {
  const [content, setContent] = useState("");
  const [page, setPage] = useState(1);
  const key = useRef<{ content: string; id: string } | null>(null);
  const cache = useQueryClient();
  const detail = useQuery({
    queryKey: ["assistant", id, page],
    queryFn: () => assistantApi.detail(id, page),
    refetchInterval: 30000,
  });
  const send = useMutation({
    mutationFn: async () => {
      const value = content.trim();
      if (!key.current || key.current.content !== value)
        key.current = { content: value, id: crypto.randomUUID() };
      return assistantApi.send(id, value, key.current.id);
    },
    onSuccess: () => {
      setContent("");
      key.current = null;
      setPage(1);
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code !== "AI_TURN_IN_PROGRESS")
        key.current = null;
    },
    onSettled: async () => {
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["assistant", id] }),
        cache.invalidateQueries({ queryKey: ["assistant-list"] }),
      ]);
    },
  });
  return (
    <section aria-label={t.title} className="min-w-0 space-y-5">
      <p className="text-sm text-muted-foreground">{t.snapshot}</p>
      {detail.isPending ? (
        <p role="status">{t.loading}</p>
      ) : detail.isError ? (
        <Failure error={detail.error} retry={() => void detail.refetch()} />
      ) : (
        <>
          <h2 className="text-xl font-semibold">
            {detail.data.conversation.title || t.untitled}
          </h2>
          {!detail.data.messages.total && <p>{t.empty}</p>}
          <div className="space-y-4">
            {detail.data.messages.items.map((message) => (
              <MessageView key={message.id} message={message} />
            ))}
          </div>
          {detail.data.messages.pages > 1 && (
            <Pager
              page={page}
              pages={detail.data.messages.pages}
              onChange={setPage}
            />
          )}
        </>
      )}
      {send.isPending && (
        <p role="status" aria-live="polite">
          {t.processing}
        </p>
      )}
      {send.isError && <Failure error={send.error} />}
      <div className="flex flex-wrap gap-2">
        {t.starters.map((starter) => (
          <Button
            key={starter}
            variant="outline"
            disabled={send.isPending}
            onClick={() => setContent(starter)}
          >
            {starter}
          </Button>
        ))}
      </div>
      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          if (content.trim() && !send.isPending) send.mutate();
        }}
      >
        <label className="grid gap-2 font-medium">
          {t.input}
          <textarea
            className={inputClass}
            rows={3}
            maxLength={2000}
            required
            value={content}
            disabled={send.isPending}
            onChange={(event) => setContent(event.target.value)}
          />
        </label>
        <Button
          type="submit"
          disabled={!content.trim() || send.isPending || detail.isError}
        >
          {send.isPending ? t.processing : t.send}
        </Button>
      </form>
    </section>
  );
}
