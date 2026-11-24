import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render } from "@testing-library/react";
import { RouterContext } from "next/dist/shared/lib/router-context.shared-runtime";
import type { NextRouter } from "next/router";
import type { ComponentProps } from "react";
import { BookCard } from "@/components/books/book-card";
import type { Book } from "@/features/catalog/api";

const open = vi.hoisted(() => vi.fn());
vi.mock("@/components/books/book-transition-provider", () => ({
  useBookTransition: () => ({ open }),
}));
const router = {
  pathname: "/catalog",
  asPath: "/catalog",
  push: vi.fn(),
  prefetch: vi.fn().mockResolvedValue(undefined),
} as unknown as NextRouter;
const book: Book = {
  id: "book",
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
const hoverMedia =
  "(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)";
let eligible: boolean;
beforeEach(() => {
  eligible = true;
  vi.useFakeTimers();
  vi.clearAllMocks();
  vi.stubGlobal("matchMedia", (query: string) =>
    Object.assign(new EventTarget(), {
      matches: query === hoverMedia && eligible,
    }),
  );
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function mount(props: Partial<ComponentProps<typeof BookCard>> = {}) {
  const view = render(
    <RouterContext.Provider value={router}>
      <BookCard book={book} animateHover {...props} />
    </RouterContext.Provider>,
  );
  const card = view.container.querySelector("article")!;
  const link = view.container.querySelector("a")!;
  const bounds = vi
    .spyOn(card, "getBoundingClientRect")
    .mockReturnValue(new DOMRect(100, 100, 200, 300));
  return { card, link, bounds, unmount: view.unmount };
}
const coords = (card: HTMLElement) =>
  ["--hover-x", "--hover-y"].map((name) => card.style.getPropertyValue(name));
const frame = () =>
  act(() => {
    vi.advanceTimersToNextFrame();
  });
const enter = (card: HTMLElement, pointerType = "mouse") =>
  fireEvent.pointerOver(card, { pointerType, clientX: 140, clientY: 175 });
function neutral(card: HTMLElement) {
  expect(card).not.toHaveAttribute("data-book-hover-active");
  expect(coords(card)).toEqual(["", ""]);
  expect(card).not.toHaveAttribute("style");
}

it("uses the most recent mouse position per frame and isolates the tilt to its card", () => {
  const onOpen = vi.fn();
  const { card, bounds } = mount({ onOpen });
  const other = mount({ book: { ...book, id: "other" } });
  const request = vi.spyOn(window, "requestAnimationFrame");
  enter(card);
  fireEvent.pointerMove(card, {
    pointerType: "mouse",
    clientX: 200,
    clientY: 250,
  });
  fireEvent.pointerMove(card, {
    pointerType: "mouse",
    clientX: 150,
    clientY: 325,
  });
  expect(request).toHaveBeenCalledTimes(1);
  frame();
  expect(card).toHaveAttribute("data-book-hover-active");
  expect(coords(card).map(Number)).toEqual([-0.5, 0.5]);
  expect(bounds).toHaveBeenCalledTimes(1);
  fireEvent.pointerMove(card, {
    pointerType: "mouse",
    clientX: 800,
    clientY: -100,
  });
  frame();
  expect(coords(card).map(Number)).toEqual([1, -1]);
  neutral(other.card);
  expect(other.bounds).not.toHaveBeenCalled();
  expect(onOpen).not.toHaveBeenCalled();
  expect(open).not.toHaveBeenCalled();
});

it.each([
  "leave",
  "pointer cancel",
  "window blur",
  "motion preference",
  "unmount",
])("clears active tilt and cancels its pending frame on %s", (reason) => {
  const { card, unmount } = mount();
  const media = vi.spyOn(window, "matchMedia");
  enter(card);
  frame();
  expect(card).toHaveAttribute("data-book-hover-active");
  const cancel = vi.spyOn(window, "cancelAnimationFrame");
  fireEvent.pointerMove(card, {
    pointerType: "mouse",
    clientX: 110,
    clientY: 110,
  });
  if (reason === "leave")
    fireEvent.pointerOut(card, {
      pointerType: "mouse",
      relatedTarget: document.body,
    });
  else if (reason === "window blur") fireEvent.blur(window);
  else if (reason === "pointer cancel") fireEvent.pointerCancel(card);
  else if (reason === "motion preference") {
    eligible = false;
    media.mock.results[0].value.dispatchEvent(new Event("change"));
  } else unmount();
  expect(cancel).toHaveBeenCalled();
  frame();
  neutral(card);
});

it.each(["default", "staff", "touch", "reduced motion"])(
  "leaves the card static with %s",
  (mode) => {
    eligible = mode !== "reduced motion";
    const { card, bounds } = mount({
      animateHover: mode === "default" ? undefined : true,
      staffRoot: mode === "staff" ? "/librarian" : undefined,
    });
    const pointerType = mode === "touch" ? "touch" : "mouse";
    enter(card, pointerType);
    fireEvent.pointerMove(card, { pointerType, clientX: 120, clientY: 110 });
    frame();
    neutral(card);
    expect(bounds).not.toHaveBeenCalled();
  },
);

it("hands a neutral cover to the opening animation and preserves click attribution", () => {
  const onOpen = vi.fn();
  const { card, link } = mount({ animateOpen: true, onOpen });
  enter(card);
  frame();
  expect(card).toHaveAttribute("data-book-hover-active");
  expect(coords(card).map(Number)).toEqual([-0.6, -0.5]);
  fireEvent.pointerMove(card, {
    pointerType: "mouse",
    clientX: 280,
    clientY: 320,
  });
  open.mockImplementationOnce(() => {
    neutral(card);
    return true;
  });
  fireEvent.click(link);
  expect(open).toHaveBeenCalledExactlyOnceWith(book, link, `/books/${book.id}`);
  expect(onOpen).toHaveBeenCalledTimes(1);
  expect(router.push).not.toHaveBeenCalled();
  frame();
  neutral(card);
});
