import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterContext } from "next/dist/shared/lib/router-context.shared-runtime";
import type { NextRouter } from "next/router";
import { useLayoutEffect, useRef, type ComponentProps } from "react";
import { BookCard } from "@/components/books/book-card";
import { measureBookCover } from "@/components/books/book-transition-geometry";
import type { BookTransitionOverlay } from "@/components/books/book-transition-overlay";
import {
  BookTransitionProvider,
  useBookTransition,
} from "@/components/books/book-transition-provider";
import { catalogApi, type Book } from "@/features/catalog/api";

const router = vi.hoisted(() => ({ push: vi.fn(), prefetch: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => window.location.pathname,
}));

// Drive visual milestones explicitly; the browser suite exercises real WAAPI timing.
const frame = vi.hoisted(() =>
  vi.fn<(props: ComponentProps<typeof BookTransitionOverlay>) => void>(),
);
vi.mock("@/components/books/book-transition-overlay", () => ({
  BookTransitionOverlay: (
    props: ComponentProps<typeof BookTransitionOverlay>,
  ) => {
    frame(props);
    return <div data-testid="overlay" data-revealing={props.revealing} />;
  },
}));

// In Vitest, next/link resolves to Next's shared router-context implementation.
const linkRouter = {
  pathname: "/catalog",
  asPath: "/catalog",
  push: vi.fn(),
  prefetch: vi.fn().mockResolvedValue(undefined),
} as unknown as NextRouter;
const book: Book = {
  id: "00000000-0000-0000-0000-000000000001",
  title: "Абай жолы",
  authors: [],
  categories: [],
  language: "kk",
  page_count: null,
  publication_year: null,
  archived_at: null,
  created_at: "",
  updated_at: "",
  cover_url: null,
  isbn: null,
  description: null,
  publisher: null,
  available_copies: 1,
  total_copies: 1,
  shelf_locations: [],
};
const href = `/books/${book.id}`;
const onOpen = vi.fn();

function Detail({ id, ready }: { id: string; ready: boolean }) {
  const heading = useRef<HTMLHeadingElement>(null);
  const report = useBookTransition()?.detailMounted;
  useLayoutEffect(() => {
    if (heading.current) report?.(id, heading.current, ready);
  }, [report, id, ready]);
  return (
    <h1 ref={heading} tabIndex={-1}>
      {book.title}
    </h1>
  );
}

function mount({
  provider = true,
  staffRoot,
  cover_url = null,
}: { provider?: boolean; staffRoot?: string; cover_url?: string | null } = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const card = (
    <BookCard
      book={{ ...book, cover_url }}
      staffRoot={staffRoot}
      animateOpen
      onOpen={onOpen}
    />
  );
  const tree = (child: React.ReactNode) => (
    <RouterContext.Provider value={linkRouter}>
      <QueryClientProvider client={client}>
        {provider ? (
          <BookTransitionProvider>{child}</BookTransitionProvider>
        ) : (
          child
        )}
      </QueryClientProvider>
    </RouterContext.Provider>
  );
  const view = render(tree(card));
  const link = screen.getByRole("link", { name: book.title });
  if (cover_url) fireEvent.error(link.querySelector("img")!);
  const jacket = link.querySelector<HTMLElement>("[data-book-cover-jacket]")!;
  jacket.style.width = "84px";
  jacket.style.height = "120px";
  vi.spyOn(jacket, "getBoundingClientRect").mockReturnValue(
    new DOMRect(8, 20, 84, 120),
  );
  return {
    link,
    jacket,
    unmount: view.unmount,
    detail(id: string, ready: boolean) {
      view.rerender(tree(<Detail id={id} ready={ready} />));
    },
  };
}

const milestone = () => frame.mock.lastCall![0];
const nativeAnimate = Object.getOwnPropertyDescriptor(
  Element.prototype,
  "animate",
);
let reduced = false;
beforeEach(() => {
  vi.useFakeTimers();
  history.replaceState(null, "", "/catalog?q=ab&page=2");
  vi.clearAllMocks();
  vi.spyOn(catalogApi, "book").mockResolvedValue(book);
  vi.stubGlobal("matchMedia", () => ({
    matches: reduced,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  Object.defineProperty(Element.prototype, "animate", {
    configurable: true,
    value: vi.fn(),
  });
});
afterEach(() => {
  cleanup();
  if (nativeAnimate)
    Object.defineProperty(Element.prototype, "animate", nativeAnimate);
  else Reflect.deleteProperty(Element.prototype, "animate");
  reduced = false;
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("opens one route for repeated activation, waits for the matching detail, then releases focus", () => {
  const view = mount();
  fireEvent.click(view.link);
  const first = milestone();
  fireEvent.click(view.link);
  act(() => {
    first.onNavigate();
    first.onNavigate();
    first.onOpened();
  });
  expect(router.push.mock.calls.map(([path]) => path)).toEqual([href]);
  expect(linkRouter.push).not.toHaveBeenCalled();
  expect(screen.getByTestId("overlay").dataset.revealing).toBe("false");
  history.replaceState(null, "", href);
  view.detail("another-book", true);
  expect(milestone().revealing).toBe(false);
  view.detail(book.id, false);
  expect(milestone().revealing).toBe(false);
  view.detail(book.id, true);
  expect(milestone().revealing).toBe(true);
  act(() => milestone().onFinished());
  expect(screen.queryByTestId("overlay")).toBeNull();
  expect(document.activeElement).toBe(screen.getByRole("heading"));
});

it.each([
  "provider absent",
  "reduced motion",
  "WAAPI unavailable",
  "staff route",
])(
  "leaves navigation and click attribution to the existing link with %s",
  (mode) => {
    reduced = mode === "reduced motion";
    if (mode === "WAAPI unavailable")
      Reflect.deleteProperty(Element.prototype, "animate");
    const staffRoot = mode === "staff route" ? "/librarian" : undefined;
    const { link } = mount({ provider: mode !== "provider absent", staffRoot });
    fireEvent.click(link);
    expect(frame).not.toHaveBeenCalled();
    expect(router.push).not.toHaveBeenCalled();
    expect(linkRouter.push).toHaveBeenCalledTimes(1);
    expect(vi.mocked(linkRouter.push).mock.calls[0][0]).toBe(
      (staffRoot ?? "") + href,
    );
    expect(onOpen).toHaveBeenCalledTimes(1);
  },
);

it("opens a failed image with the same jacket used for a missing cover", () => {
  const { link } = mount({ cover_url: "/broken.png" });
  fireEvent.click(link);
  expect(milestone().cover.kind).toBe("jacket");
  act(() => milestone().onNavigate());
  expect(router.push.mock.calls.map(([path]) => path)).toEqual([href]);
  expect(onOpen).toHaveBeenCalledTimes(1);
});

it("keeps Back authoritative even when an old animation resolves during a new transition", () => {
  const { link, jacket } = mount();
  fireEvent.click(link);
  const retired = milestone();
  act(() => {
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  expect(screen.queryByTestId("overlay")).toBeNull();
  expect(jacket.style.visibility).not.toBe("hidden");
  expect(link.closest("[inert]")).toBeNull();
  fireEvent.click(link);
  act(() => {
    retired.onNavigate();
    retired.onFinished();
  });
  expect(router.push).not.toHaveBeenCalled();
  expect(screen.queryByTestId("overlay")).toBeTruthy();
  act(() => {
    window.dispatchEvent(new Event("resize"));
  });
  expect(screen.queryByTestId("overlay")).toBeNull();
  expect(router.push.mock.calls.map(([path]) => path)).toEqual([href]);
});

it("releases the loading page at the deadline when the request is slow", async () => {
  vi.mocked(catalogApi.book).mockImplementation(() => new Promise(() => {}));
  const { link, detail } = mount();
  fireEvent.click(link);
  act(() => {
    milestone().onNavigate();
    milestone().onOpened();
  });
  history.replaceState(null, "", href);
  detail(book.id, false);
  await act(() => vi.advanceTimersByTimeAsync(2100));
  expect(screen.queryByTestId("overlay")).toBeNull();
  expect(document.body.style.overflow).not.toBe("hidden");
  expect(document.documentElement.style.overflow).not.toBe("hidden");
  expect(screen.getByRole("heading").closest("[inert]")).toBeNull();
  expect(router.push).toHaveBeenCalledTimes(1);
});

it("drops callbacks and timers when the provider unmounts before navigation", async () => {
  const view = mount();
  fireEvent.click(view.link);
  const previous = milestone();
  view.unmount();
  await act(async () => {
    previous.onNavigate();
    await vi.advanceTimersByTimeAsync(2100);
  });
  expect(router.push).not.toHaveBeenCalled();
  expect(document.querySelector("[inert]")).toBeNull();
  expect(screen.queryByTestId("overlay")).toBeNull();
});

it("measures contained image pixels at the current hover scale", () => {
  const link = document.createElement("a");
  const image = document.createElement("img");
  link.append(image);
  image.dataset.bookCoverImage = "";
  Object.assign(image.style, {
    width: "200px",
    height: "150px",
    padding: "12px",
  });
  Object.defineProperties(image, {
    complete: { value: true },
    naturalWidth: { value: 200 },
    naturalHeight: { value: 300 },
  });
  vi.spyOn(image, "getBoundingClientRect").mockReturnValue(
    new DOMRect(20, 50, 207, 155.25),
  );
  const cover = measureBookCover(link)!;
  expect(cover.source).toBe(image);
  expect(cover.rect.left).toBeCloseTo(80.03);
  expect(cover.rect.top).toBeCloseTo(62.42);
  expect(cover.rect.width).toBeCloseTo(86.94);
  expect(cover.rect.height).toBeCloseTo(130.41);
});
