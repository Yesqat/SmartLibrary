"use client";
import Image from "next/image";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  Check,
  Lightbulb,
  MessageSquare,
  Plus,
  ShieldCheck,
  Sparkles,
  Sprout,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { CatalogShell, Failure, Pager } from "@/features/catalog/shared";
import { assistant as t } from "@/locales/assistant";
import { assistantApi } from "./api";
import { Chat, ChatEmptyState } from "./chat";
import assistantBooks from "./assets/assistant-books.png";
import styles from "./assistant.module.css";

function AssistantHero() {
  return (
    <div className={styles.hero}>
      <div className={styles.heroInner}>
        <div className={styles.intro}>
          <p className={styles.eyebrow}>AI КІТАПХАНАШЫ</p>
          <p className={styles.title} aria-hidden="true">
            {t.title}
            <Sparkles />
          </p>
          <p className={styles.privacy}>{t.privacy}</p>
          <div className={styles.safety}>
            <ShieldCheck aria-hidden="true" />
            <div>
              <strong>Деректеріңізге мұқият болыңыз.</strong>
              <p>Көмекші кітапхана деректеріне сүйенеді.</p>
            </div>
          </div>
        </div>
        <div className={styles.artwork} aria-hidden="true">
          <div className={styles.speech}>
            Кітап туралы сұраңыз,
            <br />
            мен көмектесемін!
          </div>
          <Image
            src={assistantBooks}
            alt=""
            width={1536}
            height={1024}
            sizes="(max-width: 767px) 1px, (max-width: 1199px) 45vw, 470px"
            loading="eager"
          />
          <div className={styles.motto}>
            <Sprout />
            <p>Білім әрқашан жақсы серік.</p>
            <span />
          </div>
        </div>
      </div>
    </div>
  );
}

function AssistantGuide() {
  return (
    <section className={styles.guide} aria-labelledby="assistant-guide-title">
      <h2 id="assistant-guide-title">
        <Lightbulb aria-hidden="true" />
        Не сұрауға болады?
      </h2>
      <ul>
        {[
          "Кітаптар туралы ақпарат",
          "Авторлар мен жанрлар",
          "Оқу ұсыныстары",
          "Кітапхана ережелері",
          "Жалпы сұрақтар",
        ].map((item) => (
          <li key={item}>
            <Check aria-hidden="true" />
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
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
    <div className={styles.assistant}>
      <CatalogShell title={t.title}>
        <AssistantHero />
        <div className={styles.workspace}>
          <aside aria-label={t.chats} className={styles.sidebar}>
            <div className={styles.history}>
              <Button
                className={styles.newChat}
                disabled={create.isPending}
                onClick={() => create.mutate()}
              >
                <MessageSquare aria-hidden="true" />
                {t.newChat}
                <Plus aria-hidden="true" />
              </Button>
              {create.isError && <Failure error={create.error} />}
              {list.isPending ? (
                <p role="status">{t.loading}</p>
              ) : list.isError ? (
                <Failure error={list.error} retry={() => void list.refetch()} />
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
                          onClick={() => setId(row.id)}
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
            <AssistantGuide />
          </aside>
          {id ? (
            <Chat key={id} id={id} />
          ) : (
            <section className={styles.chatPanel} aria-label={t.title}>
              <header className={styles.chatHeading}>
                <span className={styles.botBadge}>
                  <Bot aria-hidden="true" />
                </span>
                <div>
                  <p>{t.empty}</p>
                  <h2>{t.newChat}</h2>
                </div>
              </header>
              <ChatEmptyState />
              <p className={styles.startHint}>
                Сол жақтан әңгіме таңдаңыз немесе «Жаңа әңгіме» бастаңыз.
              </p>
            </section>
          )}
        </div>
      </CatalogShell>
    </div>
  );
}
