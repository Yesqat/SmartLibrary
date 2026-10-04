"use client";
import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Bot, LoaderCircle, Send, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Failure, Pager, inputClass } from "@/features/catalog/shared";
import { ApiError } from "@/services/api-client";
import { assistant as t } from "@/locales/assistant";
import { assistantApi } from "./api";
import { MessageView } from "./messages";
import styles from "./assistant.module.css";

export function ChatEmptyState() {
  return (
    <div className={styles.emptyState}>
      <div className={styles.emptyIcon} aria-hidden="true">
        <BookOpen />
        <Sparkles />
      </div>
      <h3>Сұрағыңызды жазыңыз</h3>
      <p>
        Кітаптар, авторлар, жанрлар немесе кітапхана жайлы сұраңыз.
        <br />
        Мен көмектесуге дайынмын!
      </p>
    </div>
  );
}
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
    <section aria-label={t.title} className={styles.chatPanel}>
      {detail.isPending ? (
        <p role="status" className={styles.loading}>
          {t.loading}
        </p>
      ) : detail.isError ? (
        <Failure error={detail.error} retry={() => void detail.refetch()} />
      ) : (
        <>
          <header className={styles.chatHeading}>
            <span className={styles.botBadge}>
              <Bot aria-hidden="true" />
            </span>
            <div>
              <p>{t.empty}</p>
              <h2>{detail.data.conversation.title || t.untitled}</h2>
            </div>
          </header>
          {!detail.data.messages.total && <ChatEmptyState />}
          <div className={styles.messageList}>
            {detail.data.messages.items.map((message) => (
              <div
                key={message.id}
                className={
                  message.role === "USER"
                    ? styles.userMessage
                    : styles.assistantMessage
                }
              >
                <MessageView message={message} />
              </div>
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
        <p role="status" aria-live="polite" className={styles.processing}>
          <LoaderCircle aria-hidden="true" />
          {t.processing}
        </p>
      )}
      {send.isError && <Failure error={send.error} />}
      <div className={styles.composer}>
        <p className={styles.snapshot}>{t.snapshot}</p>
        <div className={styles.starters}>
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
          className={styles.sendForm}
          onSubmit={(event) => {
            event.preventDefault();
            if (content.trim() && !send.isPending) send.mutate();
          }}
        >
          <label className={styles.inputLabel}>
            {t.input}
            <textarea
              className={inputClass}
              placeholder="Сұрағыңызды жазыңыз..."
              rows={3}
              maxLength={2000}
              required
              value={content}
              disabled={send.isPending}
              onChange={(event) => setContent(event.target.value)}
            />
          </label>
          <Button
            className={styles.sendButton}
            type="submit"
            disabled={!content.trim() || send.isPending || detail.isError}
          >
            {send.isPending ? (
              <LoaderCircle aria-hidden="true" />
            ) : (
              <Send aria-hidden="true" />
            )}
            <span className="sr-only">
              {send.isPending ? t.processing : t.send}
            </span>
          </Button>
        </form>
      </div>
    </section>
  );
}
