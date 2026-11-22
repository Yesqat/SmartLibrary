"use client";

import { useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { bookDetailQuery, type Book } from "@/features/catalog/api";
import { catalog } from "@/locales/catalog";
import {
  measureBookCover,
  type BookCoverSnapshot,
} from "./book-transition-geometry";
import { BookTransitionOverlay } from "./book-transition-overlay";

type BookTransition = {
  open: (book: Book, link: HTMLElement, href: string) => boolean;
  detailMounted: (
    id: string,
    heading: HTMLHeadingElement,
    ready: boolean,
  ) => void;
};
const Context = createContext<BookTransition | null>(null);
export const useBookTransition = () => useContext(Context);

type Flight = {
  token: number;
  id: string;
  href: string;
  origin: string;
  link: HTMLElement;
  cover: BookCoverSnapshot;
  pushed: boolean;
  heading?: HTMLHeadingElement;
};

const reducedMotion = "(prefers-reduced-motion: reduce)";

export function BookTransitionProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const cache = useQueryClient();
  const content = useRef<HTMLDivElement>(null);
  const sequence = useRef(0);
  const active = useRef<Flight | null>(null);
  const [flight, setFlight] = useState<Flight | null>(null);
  const [opened, setOpened] = useState(false);
  const [ready, setReady] = useState(false);

  const open = useCallback<BookTransition["open"]>(
    (book, link, href) => {
      // Claim the click synchronously, including two clicks in the same render.
      if (active.current) return true;
      if (
        typeof Element.prototype.animate !== "function" ||
        !window.matchMedia ||
        window.matchMedia(reducedMotion).matches
      )
        return false;
      const cover = measureBookCover(link);
      if (!cover) return false;
      const next = {
        token: ++sequence.current,
        id: book.id,
        href,
        origin: window.location.href,
        link,
        cover,
        pushed: false,
      };
      active.current = next;
      setOpened(false);
      setReady(false);
      setFlight(next);
      router.prefetch(href);
      void cache.prefetchQuery(bookDetailQuery(book.id));
      return true;
    },
    [cache, router],
  );

  const detailMounted = useCallback<BookTransition["detailMounted"]>(
    (id, heading, ready) => {
      const current = active.current;
      if (!current || current.id !== id || !current.pushed) return;
      current.heading = heading;
      setReady(ready);
    },
    [],
  );
  const context = useMemo(
    () => ({ open, detailMounted }),
    [open, detailMounted],
  );

  const finish = useCallback((current: Flight) => {
    if (active.current !== current) return;
    active.current = null;
    setFlight(null);
  }, []);

  const navigate = useCallback(
    (current: Flight) => {
      if (active.current !== current || current.pushed) return;
      if (window.location.href !== current.origin) {
        finish(current);
        return;
      }
      current.pushed = true;
      router.push(current.href);
    },
    [finish, router],
  );

  const skipMotion = useCallback(
    (current: Flight) => {
      navigate(current);
      finish(current);
    },
    [finish, navigate],
  );

  useLayoutEffect(() => {
    if (!flight) return;
    if (window.location.href !== flight.origin && pathname !== flight.href)
      finish(flight);
  }, [finish, flight, pathname]);

  useLayoutEffect(() => {
    const page = content.current;
    if (!flight || !page) return;
    const root = document.documentElement;
    const { overflow, scrollbarGutter } = root.style;
    if (root.clientWidth < window.innerWidth)
      root.style.scrollbarGutter = "stable";
    root.style.overflow = "hidden";
    page.inert = true;

    const cancel = () => finish(flight);
    const skip = () => skipMotion(flight);
    const preference = window.matchMedia(reducedMotion);
    const onPreference = () => {
      if (preference.matches) skip();
    };
    const deadline = window.setTimeout(skip, 2000);
    window.addEventListener("popstate", cancel);
    window.addEventListener("pagehide", cancel);
    window.addEventListener("resize", skip);
    window.addEventListener("orientationchange", skip);
    preference.addEventListener("change", onPreference);
    return () => {
      window.clearTimeout(deadline);
      window.removeEventListener("popstate", cancel);
      window.removeEventListener("pagehide", cancel);
      window.removeEventListener("resize", skip);
      window.removeEventListener("orientationchange", skip);
      preference.removeEventListener("change", onPreference);
      root.style.overflow = overflow;
      root.style.scrollbarGutter = scrollbarGutter;
      page.inert = false;
      if (
        window.location.pathname === flight.href &&
        flight.heading?.isConnected
      )
        flight.heading.focus({ preventScroll: true });
      else if (
        window.location.href === flight.origin &&
        flight.link.isConnected
      )
        flight.link.focus({ preventScroll: true });
    };
  }, [finish, flight, skipMotion]);

  useLayoutEffect(
    () => () => {
      active.current = null;
    },
    [],
  );

  return (
    <Context.Provider value={context}>
      <div ref={content} className="contents">
        {children}
      </div>
      {flight && (
        <>
          <span className="sr-only" role="status">
            {catalog.openingBook}
          </span>
          <BookTransitionOverlay
            key={flight.token}
            cover={flight.cover}
            revealing={opened && ready && pathname === flight.href}
            onNavigate={() => navigate(flight)}
            onOpened={() => {
              if (active.current === flight) setOpened(true);
            }}
            onFinished={() => finish(flight)}
            onCancel={() => skipMotion(flight)}
          />
        </>
      )}
    </Context.Provider>
  );
}
