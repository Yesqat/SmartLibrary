"use client";
import { useEffect, useRef, type ReactNode } from "react";
import { BookOpen, LoaderCircle, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { BookCard } from "@/components/books/book-card";
import { useAuth } from "@/features/auth/auth-provider";
import { Failure } from "@/features/catalog/shared";
import { recommendations as t } from "@/locales/recommendations";
import { recommendationApi, type RecommendationItem } from "./api";
import styles from "./recommendations.module.css";

export function RecommendationCard({
  item,
  receipt,
}: {
  item: RecommendationItem;
  receipt?: string | null;
}) {
  const element = useRef<HTMLDivElement>(null);
  const impression = useRef<Promise<string> | null>(null);
  const record = () => {
    if (!receipt) return Promise.resolve(null);
    if (!impression.current) {
      impression.current = recommendationApi
        .impression(receipt, item.book.id)
        .then((row) => row.id)
        .catch((error: unknown) => {
          impression.current = null;
          throw error;
        });
    }
    return impression.current;
  };
  const recordRef = useRef(record);
  useEffect(() => {
    recordRef.current = record;
  });
  useEffect(() => {
    if (
      !receipt ||
      !element.current ||
      typeof IntersectionObserver === "undefined"
    )
      return;
    let visible = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const update = () => {
      clearTimeout(timer);
      if (visible && document.visibilityState === "visible") {
        timer = setTimeout(() => {
          void recordRef.current().catch(() => undefined);
        }, 1000);
      }
    };
    const observer = new IntersectionObserver(
      ([entry]) => {
        visible = entry.isIntersecting && entry.intersectionRatio >= 0.5;
        update();
      },
      { threshold: 0.5 },
    );
    observer.observe(element.current);
    document.addEventListener("visibilitychange", update);
    return () => {
      clearTimeout(timer);
      observer.disconnect();
      document.removeEventListener("visibilitychange", update);
    };
  }, [receipt]);
  return (
    <div ref={element} className={styles.item}>
      <BookCard
        book={item.book}
        animateHover
        onOpen={() => {
          // An explicit click proves rendering even if it precedes the dwell threshold.
          void record()
            .then((id) => (id ? recommendationApi.click(id) : undefined))
            .catch(() => undefined);
        }}
      />
      <p className={styles.reason}>
        <Sparkles aria-hidden="true" />
        {t.reasons[item.reason]}
      </p>
    </div>
  );
}

export function RecommendationSection({
  kind,
  bookId,
  headingAction,
}: {
  kind: "popular" | "similar" | "personalized";
  bookId?: string;
  headingAction?: ReactNode;
}) {
  const { user, status } = useAuth();
  const result = useQuery({
    queryKey: ["recommendations", kind, bookId, user?.id ?? "public"],
    queryFn: () => recommendationApi.list(kind, bookId),
    enabled:
      status !== "loading" &&
      (kind !== "personalized" || user?.role === "READER"),
    staleTime: 60000,
  });
  if (kind === "personalized" && user?.role !== "READER") return null;
  return (
    <section className={styles.section} aria-label={t.titles[kind]}>
      <h2 className={styles.heading}>{t.titles[kind]}</h2>
      {headingAction}
      {result.isPending ? (
        <p role="status" className={styles.notice}>
          <LoaderCircle className={styles.loader} aria-hidden="true" />
          {t.loading}
        </p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          {result.data.indexing_pending && (
            <p role="status" className={styles.pending}>
              {t.pending}
            </p>
          )}
          {!result.data.items.length && (
            <p className={styles.notice}>
              <BookOpen aria-hidden="true" />
              {kind === "similar" &&
              !result.data.content_available &&
              !result.data.indexing_pending
                ? t.unavailable
                : t.empty}
            </p>
          )}
          <div className={styles.grid}>
            {result.data.items.map((item) => (
              <RecommendationCard
                key={`${item.book.id}:${result.data.receipt ?? "public"}`}
                item={item}
                receipt={result.data.receipt}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
