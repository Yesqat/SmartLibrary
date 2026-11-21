"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AudioLines,
  BookMarked,
  BookOpen,
  ChevronDown,
  Feather,
  History,
  LibraryBig,
  MessageSquare,
  MessageSquarePlus,
  Rotate3d,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { CatalogNavigation, Failure, Pager } from "@/features/catalog/shared";
import { assistant as t } from "@/locales/assistant";
import { assistantApi } from "./api";
import { Chat } from "./chat";
import { LibrarianPortrait } from "./librarian-portrait";
import styles from "./assistant.module.css";

const topics = [
  {
    icon: BookOpen,
    title: "Кітаптар мен авторлар",
    example: "Абайдың қандай кітаптары бар?",
  },
  {
    icon: Sparkles,
    title: "Оқу ұсыныстары",
    example: "Маған тарихи роман ұсына аласыз ба?",
  },
  {
    icon: BookMarked,
    title: "Менің кітаптарым",
    example: "Кітаптарымды қашан қайтаруым керек?",
  },
  {
    icon: LibraryBig,
    title: "Кітапхана ережелері",
    example: "Кітапты қалай брондаймын?",
  },
];

function AssistantGuide({ compact = false }: { compact?: boolean }) {
  return (
    <section
      className={compact ? styles.compactGuide : styles.guide}
      aria-labelledby="assistant-guide-title"
    >
      <div className={styles.guideHeading}>
        <Feather aria-hidden="true" />
        <h2 id="assistant-guide-title">Не сұрауға болады?</h2>
      </div>
      {!compact && (
        <p className={styles.guideIntro}>
          Сұрағыңызды өз сөзіңізбен қойыңыз. Мына мысалдардан бастауға болады.
        </p>
      )}
      <ul className={styles.topics}>
        {topics.map(({ icon: Icon, title, example }) => (
          <li key={title}>
            <span className={styles.topicIcon}>
              <Icon aria-hidden="true" />
            </span>
            <div>
              <strong>{title}</strong>
              {!compact && <p>«{example}»</p>}
            </div>
          </li>
        ))}
      </ul>
      {!compact && (
        <p className={styles.startHint}>
          <MessageSquare aria-hidden="true" />
          «Жаңа әңгіме» батырмасын басыңыз немесе тізімнен бұрынғы сұхбатты
          таңдаңыз.
        </p>
      )}
    </section>
  );
}

export function AssistantPage() {
  const [id, setId] = useState("");
  const [page, setPage] = useState(1);
  const [isTyping, setIsTyping] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
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
    <div className={styles.assistant} data-chat-open={Boolean(id) || undefined}>
      <header>
        <CatalogNavigation currentHref="/assistant" />
      </header>
      <main className={styles.main}>
        <section className={styles.hero} aria-labelledby="assistant-heading">
          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}>
              <AudioLines aria-hidden="true" />
              Оқырман көмекшісі
            </p>
            <h1 id="assistant-heading">{t.title}</h1>
            <p className={styles.heroDescription}>
              Кітап таңдауға көмектесемін. Автор, жанр немесе кітапты қайтару
              мерзімі туралы сұраңыз.
            </p>
            <Button
              className={styles.newChat}
              disabled={create.isPending}
              onClick={() => create.mutate()}
            >
              <MessageSquarePlus aria-hidden="true" />
              {t.newChat}
            </Button>
          </div>
          <div className={styles.stage}>
            <div className={styles.halo} aria-hidden="true" />
            <div className={styles.orbit} aria-hidden="true" />
            <div className={styles.portrait}>
              <LibrarianPortrait isTyping={isTyping} />
            </div>
            <span className={styles.turnHint} aria-hidden="true">
              <Rotate3d /> Сырғытып бұрыңыз
            </span>
          </div>
        </section>
        {create.isError && <Failure error={create.error} />}
        <div className={styles.safety}>
          <ShieldCheck aria-hidden="true" />
          <p>{t.privacy}</p>
        </div>
        <div className={styles.workspace}>
          <aside
            aria-label={t.chats}
            className={styles.sidebar}
            onBlur={(event) => {
              if (
                historyOpen &&
                !event.currentTarget.contains(event.relatedTarget)
              )
                setHistoryOpen(false);
            }}
          >
            {id && (
              <button
                type="button"
                className={styles.historyToggle}
                aria-expanded={historyOpen}
                aria-controls="assistant-history"
                onClick={() => setHistoryOpen(!historyOpen)}
              >
                <History aria-hidden="true" />
                {t.chats}
                <ChevronDown aria-hidden="true" />
              </button>
            )}
            <div
              id="assistant-history"
              className={styles.sidebarPanels}
              data-open={historyOpen || undefined}
            >
              <div className={styles.history}>
                <div className={styles.historyHeading}>
                  <History aria-hidden="true" />
                  <h2>{t.chats}</h2>
                  {list.data && <span>{list.data.total}</span>}
                </div>
                {list.isPending ? (
                  <p role="status">{t.loading}</p>
                ) : list.isError ? (
                  <Failure
                    error={list.error}
                    retry={() => void list.refetch()}
                  />
                ) : (
                  <>
                    {!list.data.total && (
                      <p className={styles.noChats}>{t.noChats}</p>
                    )}
                    <ul className={styles.conversations}>
                      {list.data.items.map((row) => (
                        <li key={row.id}>
                          <button
                            className={styles.conversation}
                            aria-current={id === row.id ? "true" : undefined}
                            onClick={() => {
                              setId(row.id);
                              setHistoryOpen(false);
                            }}
                          >
                            <MessageSquare aria-hidden="true" />
                            <span>{row.title || t.untitled}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                    {list.data.pages > 1 && (
                      <Pager
                        page={page}
                        pages={list.data.pages}
                        onChange={setPage}
                      />
                    )}
                  </>
                )}
              </div>
              {id && <AssistantGuide compact />}
            </div>
          </aside>
          {id ? (
            <Chat key={id} id={id} onTypingChange={setIsTyping} />
          ) : (
            <AssistantGuide />
          )}
        </div>
      </main>
    </div>
  );
}
