import "@testing-library/jest-dom/vitest";
import { createRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { afterEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { readerApi } from "@/features/reader/api";
import { FavoriteButton } from "@/features/reader/favorites";
import { reader as t } from "@/locales/reader";

const auth = vi.hoisted(() => ({ user: { id: "reader", role: "READER" } }));
vi.mock("@/features/auth/auth-provider", () => ({ useAuth: () => auth }));

const nativeAnimate = Object.getOwnPropertyDescriptor(
  Element.prototype,
  "animate",
);
afterEach(() => {
  cleanup();
  if (nativeAnimate)
    Object.defineProperty(Element.prototype, "animate", nativeAnimate);
  else Reflect.deleteProperty(Element.prototype, "animate");
  auth.user = { id: "reader", role: "READER" };
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function mockAnimations(reduced = false) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: reduced && query.includes("prefers-reduced-motion"),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  const animate = vi.fn(function (this: Element) {
    const finished = Promise.withResolvers<void>();
    return {
      finished: finished.promise,
      finish: finished.resolve,
      cancel: vi.fn(() =>
        finished.reject(new DOMException("Cancelled", "AbortError")),
      ),
    };
  });
  Object.defineProperty(Element.prototype, "animate", {
    configurable: true,
    value: animate,
  });
  return animate;
}

const cover = "/test-cover.jpg";
function mount({
  coverUrl = cover,
  initial,
}: { coverUrl?: string | null; initial?: boolean } = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const sourceRef = createRef<HTMLImageElement>();
  const tree = (id: string) => (
    <QueryClientProvider client={client}>
      <nav style={{ overflowX: "auto" }}>
        <Link href="/favorites" data-favorites-target="">
          {t.favorites}
        </Link>
      </nav>
      {coverUrl && (
        <Image
          ref={sourceRef}
          src={coverUrl}
          width={120}
          height={180}
          alt="Original cover"
          unoptimized
        />
      )}
      <FavoriteButton
        bookId={id}
        initial={initial}
        coverUrl={coverUrl}
        sourceRef={sourceRef}
      />
    </QueryClientProvider>
  );
  const view = render(tree("book"));
  const source = sourceRef.current;
  if (source) {
    Object.defineProperties(source, {
      complete: { value: true, configurable: true },
      currentSrc: { value: source.src },
      naturalWidth: { value: 400 },
      naturalHeight: { value: 600 },
    });
    vi.spyOn(source, "getBoundingClientRect").mockReturnValue(
      new DOMRect(80, 200, 120, 180),
    );
  }
  const nav = screen.getByRole("navigation");
  vi.spyOn(nav, "getBoundingClientRect").mockReturnValue(
    new DOMRect(0, 0, 340, 60),
  );
  const target = screen.getByRole("link");
  const targetRect = vi
    .spyOn(target, "getBoundingClientRect")
    .mockReturnValue(new DOMRect(220, 10, 90, 36));
  return {
    client,
    source,
    nav,
    target,
    targetRect,
    unmount: view.unmount,
    showBook: (id: string) => view.rerender(tree(id)),
  };
}

const copy = () =>
  document.querySelector<HTMLImageElement>("img[data-favorite-flight]");
async function readyButton() {
  const button = screen.getByRole("button");
  await waitFor(() => expect(button).toBeEnabled());
  return button;
}

it("flies the actual cover once after the add is saved, while invalidations retain control of pending", async () => {
  const write = Promise.withResolvers<void>();
  const refetch = Promise.withResolvers<{ is_favorite: boolean }>();
  vi.spyOn(readerApi, "favorite")
    .mockResolvedValueOnce({ is_favorite: false })
    .mockReturnValueOnce(refetch.promise)
    .mockResolvedValue({ is_favorite: true });
  const setFavorite = vi
    .spyOn(readerApi, "setFavorite")
    .mockReturnValue(write.promise);
  const animate = mockAnimations();
  const { client, source, target } = mount();
  const invalidate = vi.spyOn(client, "invalidateQueries");
  const button = await readyButton();
  button.focus();
  const location = window.location.href;
  const scroll = [window.scrollX, window.scrollY];
  act(() => {
    button.click();
    button.click();
  });
  await waitFor(() => expect(setFavorite).toHaveBeenCalledTimes(1));
  expect(setFavorite).toHaveBeenCalledWith("book", true);
  expect(button).toBeDisabled();
  expect(button).toHaveAttribute("aria-pressed", "false");
  expect(animate).not.toHaveBeenCalled();
  expect(copy()).toBeNull();

  await act(async () => write.resolve());
  await waitFor(() => expect(copy()).toBeInTheDocument());
  const flying = copy()!;
  expect(flying.src).toBe(source!.src);
  expect(flying).toHaveAttribute("alt", "");
  expect(flying.closest('[aria-hidden="true"]')).toBeInTheDocument();
  expect(animate.mock.contexts).toContain(button.querySelector("svg"));
  expect(
    animate.mock.contexts.filter(
      (element) => element instanceof HTMLImageElement,
    ),
  ).toEqual([flying]);
  expect(invalidate.mock.calls.map(([filter]) => filter?.queryKey)).toEqual([
    ["favorites"],
    ["recommendations"],
    ["reader-summary"],
  ]);
  expect(button).toBeDisabled();

  await act(async () => refetch.resolve({ is_favorite: true }));
  expect(await screen.findByRole("status")).toHaveTextContent(t.favoriteAdded);
  expect(button).toBeEnabled();
  expect(button).toHaveAttribute("aria-pressed", "true");
  expect(copy()).toBe(flying);
  const flight =
    animate.mock.results[animate.mock.contexts.indexOf(flying)].value;
  await act(async () => flight.finish());
  await waitFor(() => expect(copy()).toBeNull());
  expect(animate.mock.contexts).toContain(target);
  expect(source).toBeInTheDocument();
  expect(button).toHaveFocus();
  expect(window.location.href).toBe(location);
  expect([window.scrollX, window.scrollY]).toEqual(scroll);
});

it("reports a rejected add without starting feedback", async () => {
  vi.spyOn(readerApi, "favorite").mockResolvedValue({ is_favorite: false });
  vi.spyOn(readerApi, "setFavorite").mockRejectedValue(
    new Error("write failed"),
  );
  const animate = mockAnimations();
  mount();
  const button = await readyButton();
  fireEvent.click(button);
  expect(await screen.findByRole("alert")).toBeVisible();
  expect(button).toHaveAttribute("aria-pressed", "false");
  expect(screen.queryByRole("status")).toBeNull();
  expect(animate).not.toHaveBeenCalled();
  expect(copy()).toBeNull();
});

it("keeps an existing favorite still on load and removal", async () => {
  vi.spyOn(readerApi, "favorite")
    .mockResolvedValueOnce({ is_favorite: true })
    .mockResolvedValue({ is_favorite: false });
  const save = vi.spyOn(readerApi, "setFavorite").mockResolvedValue(undefined);
  const animate = mockAnimations();
  mount({ initial: true });
  fireEvent.click(
    await screen.findByRole("button", { name: t.removeFavorite }),
  );
  expect(await screen.findByRole("status")).toHaveTextContent(
    t.favoriteRemoved,
  );
  expect(save).toHaveBeenCalledWith("book", false);
  expect(animate).not.toHaveBeenCalled();
  expect(copy()).toBeNull();
});

it("does not query favorites or expose the action to a librarian", () => {
  auth.user.role = "LIBRARIAN";
  const query = vi.spyOn(readerApi, "favorite");
  const animate = mockAnimations();
  mount();
  expect(screen.queryByRole("button")).toBeNull();
  expect(query).not.toHaveBeenCalled();
  expect(animate).not.toHaveBeenCalled();
});

it.each([
  "reduced motion",
  "missing cover",
  "unloaded cover",
  "clipped target",
  "WAAPI unavailable",
  "WAAPI error",
])("keeps a successful add working with %s", async (mode) => {
  const write = Promise.withResolvers<void>();
  vi.spyOn(readerApi, "favorite")
    .mockResolvedValueOnce({ is_favorite: false })
    .mockResolvedValue({ is_favorite: true });
  vi.spyOn(readerApi, "setFavorite").mockReturnValue(write.promise);
  const animate = mockAnimations(mode === "reduced motion");
  if (mode === "WAAPI unavailable")
    Reflect.deleteProperty(Element.prototype, "animate");
  if (mode === "WAAPI error")
    animate.mockImplementation(() => {
      throw new Error("Animation unavailable");
    });
  const { source, targetRect } = mount({
    coverUrl: mode === "missing cover" ? null : cover,
  });
  const button = await readyButton();
  fireEvent.click(button);
  // Move the link during the request. It is still in the window, but outside its nav.
  if (mode === "clipped target")
    targetRect.mockReturnValue(new DOMRect(400, 10, 90, 36));
  if (mode === "unloaded cover")
    Object.defineProperty(source, "complete", { value: false });
  await act(async () => write.resolve());
  expect(await screen.findByRole("status")).toHaveTextContent(t.favoriteAdded);
  expect(button).toHaveAttribute("aria-pressed", "true");
  expect(copy()).toBeNull();
  if (mode === "reduced motion" || mode === "WAAPI unavailable")
    expect(animate).not.toHaveBeenCalled();
  else if (mode !== "WAAPI error")
    expect(animate.mock.contexts).toEqual([button.querySelector("svg")]);
});

it.each(["unmount", "another book", "another reader"])(
  "ignores a late add after %s",
  async (change) => {
    const write = Promise.withResolvers<void>();
    vi.spyOn(readerApi, "favorite").mockResolvedValue({ is_favorite: false });
    vi.spyOn(readerApi, "setFavorite").mockReturnValue(write.promise);
    const animate = mockAnimations();
    const view = mount();
    fireEvent.click(await readyButton());
    await waitFor(() => expect(readerApi.setFavorite).toHaveBeenCalledTimes(1));
    if (change === "unmount") view.unmount();
    else if (change === "another book") view.showBook("second-book");
    else {
      auth.user = { ...auth.user, id: "second-reader" };
      view.showBook("book");
    }
    await act(async () => write.resolve());
    await waitFor(() => expect(view.client.isMutating()).toBe(0));
    expect(animate).not.toHaveBeenCalled();
    expect(copy()).toBeNull();
  },
);

it.each(["nav scroll", "resize", "remove"])(
  "cancels an in-flight cover without highlighting a stale target on %s",
  async (event) => {
    let saved = false;
    vi.spyOn(readerApi, "favorite").mockImplementation(async () => ({
      is_favorite: saved,
    }));
    vi.spyOn(readerApi, "setFavorite").mockImplementation(
      async (_id, enabled) => {
        saved = enabled;
      },
    );
    const animate = mockAnimations();
    const { nav, target } = mount();
    fireEvent.click(await readyButton());
    expect(await screen.findByRole("status")).toHaveTextContent(
      t.favoriteAdded,
    );
    const flying = copy()!;
    expect(flying).toBeInTheDocument();
    const flight =
      animate.mock.results[animate.mock.contexts.indexOf(flying)].value;
    if (event === "nav scroll") fireEvent.scroll(nav);
    else if (event === "resize") fireEvent(window, new Event("resize"));
    else fireEvent.click(await readyButton());
    await waitFor(() => expect(copy()).toBeNull());
    expect(flight.cancel).toHaveBeenCalled();
    expect(animate.mock.contexts).not.toContain(target);
    await waitFor(() =>
      expect(screen.getByRole("button")).toHaveAttribute(
        "aria-pressed",
        String(event !== "remove"),
      ),
    );
  },
);
