"use client";

import { type PointerEvent, useCallback, useLayoutEffect, useRef } from "react";
import type { Book } from "@/features/catalog/api";

const hoverMedia =
  "(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)";

type Hover = {
  card: HTMLElement;
  listeners: AbortController;
  frame: number | null;
  clientX: number;
  clientY: number;
};

function normalize(position: number, start: number, size: number) {
  return Math.max(-1, Math.min(1, ((position - start) / size) * 2 - 1));
}

export function useBookHover(enabled: boolean, book: Book) {
  const current = useRef<Hover | null>(null);
  const reset = useCallback(() => {
    const hover = current.current;
    if (!hover) return;
    current.current = null;
    if (hover.frame !== null) cancelAnimationFrame(hover.frame);
    hover.listeners.abort();
    delete hover.card.dataset.bookHoverActive;
    hover.card.style.removeProperty("--hover-x");
    hover.card.style.removeProperty("--hover-y");
    if (hover.card.getAttribute("style") === "")
      hover.card.removeAttribute("style");
  }, []);

  useLayoutEffect(() => reset, [enabled, book, reset]);

  function track(event: PointerEvent<HTMLElement>) {
    if (event.pointerType !== "mouse") {
      reset();
      return;
    }
    let hover = current.current;
    if (!hover) {
      const media = window.matchMedia?.(hoverMedia);
      if (!media?.matches || !media.addEventListener) return;
      const listeners = new AbortController();
      const { signal } = listeners;
      window.addEventListener("blur", reset, { signal });
      window.addEventListener("pagehide", reset, { signal });
      media.addEventListener("change", reset, { signal });
      hover = {
        card: event.currentTarget,
        listeners,
        frame: null,
        clientX: 0,
        clientY: 0,
      };
      current.current = hover;
    }
    hover.clientX = event.clientX;
    hover.clientY = event.clientY;
    if (hover.frame !== null) return;
    hover.frame = requestAnimationFrame(() => {
      hover.frame = null;
      const { card, clientX, clientY } = hover;
      const rect = card.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return reset();
      card.style.setProperty(
        "--hover-x",
        String(normalize(clientX, rect.left, rect.width)),
      );
      card.style.setProperty(
        "--hover-y",
        String(normalize(clientY, rect.top, rect.height)),
      );
      card.dataset.bookHoverActive = "";
    });
  }

  return {
    reset,
    handlers: enabled
      ? {
          onPointerEnter: track,
          onPointerMove: track,
          onPointerLeave: reset,
          onPointerCancel: reset,
        }
      : undefined,
  };
}
