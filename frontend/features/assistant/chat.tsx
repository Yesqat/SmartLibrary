"use client";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, LoaderCircle, MessagesSquare, Send } from "lucide-react";
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
      </div>
      <h3>Сұрағыңызды жазыңыз</h3>
      <p>Кітаптар, авторлар, жанрлар немесе кітапхана жайлы сұраңыз.</p>
    </div>
  );
}
export function Chat({
  id,
  onTypingChange,
}: {
  id: string;
  onTypingChange?: (typing: boolean) => void;
}) {
  const [content, setContent] = useState("");
  const [page, setPage] = useState(1);
  const key = useRef<{ content: string; id: string } | null>(null);
  const typingTimeout = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    return () => {
      clearTimeout(typingTimeout.current);
      onTypingChange?.(false);
    };
  }, [onTypingChange]);

  function indicateTyping(typing: boolean) {
    if (!onTypingChange) return;
    clearTimeout(typingTimeout.current);
    onTypingChange(typing);
    if (typing) {
      typingTimeout.current = setTimeout(() => onTypingChange(false), 1400);
    }
  }

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
      {detail.isSuccess && (
        <header className={styles.chatHeading}>
          <span className={styles.botBadge}>
            <MessagesSquare aria-hidden="true" />
          </span>
          <div>
            <h2>{detail.data.conversation.title || t.untitled}</h2>
            <p>{t.empty}</p>
          </div>
        </header>
      )}
      <div
        className={styles.transcript}
        role="region"
        aria-label="Хабарламалар"
        tabIndex={0}
      >
        <div className={styles.transcriptBody}>
          <p className={styles.snapshot}>{t.snapshot}</p>
          {detail.isPending ? (
            <p role="status" className={styles.loading}>
              {t.loading}
            </p>
          ) : detail.isError ? (
            <Failure error={detail.error} retry={() => void detail.refetch()} />
          ) : (
            <>
              {detail.data.messages.pages > 1 && (
                <Pager
                  page={page}
                  pages={detail.data.messages.pages}
                  onChange={setPage}
                />
              )}
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
            </>
          )}
        </div>
      </div>
      {send.isPending && (
        <p role="status" aria-live="polite" className={styles.processing}>
          <LoaderCircle aria-hidden="true" />
          {t.processing}
        </p>
      )}
      {send.isError && <Failure error={send.error} />}
      <div className={styles.composer} onSubmit={() => indicateTyping(false)}>
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
              onInput={() => indicateTyping(true)}
              onBlur={() => indicateTyping(false)}
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
