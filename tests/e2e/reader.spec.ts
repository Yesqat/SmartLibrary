import { randomUUID } from "node:crypto";
import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { apiLogin, apiReader, pageLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });
test("Reader favorites, notifications, profile, owned loans and reservation history", async ({
  page,
  request,
}) => {
  test.setTimeout(100000);
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD required");
  const staff = await apiLogin(
    request,
    "librarian@smartlibrary.example",
    password,
  );
  const response = await request.post("/api/v1/books", {
    headers: staff,
    data: { title: `Оқырман тексеруі ${randomUUID()}`, language: "kk" },
  });
  expect(response.status()).toBe(201);
  const book = await response.json();
  expect(
    (
      await request.post(`/api/v1/books/${book.id}/copies`, {
        headers: staff,
        data: { inventory_number: `READER-${randomUUID()}` },
      })
    ).status(),
  ).toBe(201);
  const reader = await apiReader(request);
  let reservationId: string | undefined;
  try {
    await pageLogin(page, reader.email, reader.password, /\/dashboard$/);
    await page.goto(`/books/${book.id}`);
    await page
      .getByRole("button", { name: "Таңдаулыға қосу", exact: true })
      .click();
    await expect(
      page.getByText("Таңдаулыға қосылды", { exact: true }),
    ).toBeVisible();
    await page.goto("/favorites");
    await expect(
      page.getByRole("link", { name: book.title, exact: true }),
    ).toBeVisible();
    const reserved = await request.post("/api/v1/reservations", {
      headers: reader.headers,
      data: { book_id: book.id },
    });
    expect(reserved.status()).toBe(201);
    reservationId = (await reserved.json()).id;
    await page.goto("/notifications");
    await expect(
      page.getByRole("button", { name: "Оқылды деп белгілеу", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", {
        name: "Барлығын оқылды деп белгілеу",
        exact: true,
      })
      .click();
    await expect(page.getByText("Хабарламалар жаңартылды")).toBeVisible();
    expect(
      (
        await (
          await request.get("/api/v1/notifications?unread=true", {
            headers: reader.headers,
          })
        ).json()
      ).total,
    ).toBe(0);
    await page.goto("/account/profile");
    await page.getByLabel("Аты", { exact: true }).fill("Айдана");
    await page
      .locator("form")
      .filter({ has: page.getByLabel("Аты", { exact: true }) })
      .getByRole("button", { name: "Сақтау", exact: true })
      .click();
    await expect(
      page.getByRole("status").filter({ hasText: "Сақталды" }),
    ).toBeVisible();
    const me = await (
      await request.get("/api/v1/users/me", { headers: reader.headers })
    ).json();
    expect(me.first_name).toBe("Айдана");
    expect(me.role).toBe("READER");
    await page.goto("/my-books");
    await expect(
      page.getByText(
        "Кітапты кітапханаға әкеліңіз. Физикалық қайтаруды кітапханашы тіркейді.",
      ),
    ).toBeVisible();
    expect(
      await page.getByRole("button", { name: /Қайтаруды тіркеу/ }).count(),
    ).toBe(0);
    expect(
      (
        await request.post(`/api/v1/reservations/${reservationId}/cancel`, {
          headers: reader.headers,
        })
      ).status(),
    ).toBe(200);
    await page.goto("/reservations");
    await page.getByRole("button", { name: "Оқу тарихы", exact: true }).click();
    await expect(
      page.getByRole("link", { name: book.title, exact: true }),
    ).toBeVisible();
    await page.goto("/history");
    await expect(
      page.getByRole("heading", { name: "Оқу тарихы", exact: true }),
    ).toBeVisible();
  } finally {
    if (reservationId)
      await request.post(`/api/v1/reservations/${reservationId}/cancel`, {
        headers: reader.headers,
      });
    await request.delete(`/api/v1/favorites/${book.id}`, {
      headers: reader.headers,
    });
    expect(
      (
        await request.patch(`/api/v1/books/${book.id}/archive`, {
          headers: staff,
          data: { archived: true },
        })
      ).status(),
    ).toBe(200);
  }
});

test("a reader's saved book cover flies only to a visible Favorites link", async ({
  page,
  request,
}) => {
  test.setTimeout(100000);
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD required");
  const staff = await apiLogin(
    request,
    "librarian@smartlibrary.example",
    password,
  );
  const reader = await apiReader(request);
  const title = `Мұқаба ${randomUUID().slice(0, 8)}`;
  const created = await request.post("/api/v1/books", {
    headers: staff,
    data: { title, language: "kk" },
  });
  expect(created.status()).toBe(201);
  const { id } = await created.json();
  const bookApi = `/api/v1/books/${id}`;
  try {
    const uploaded = await request.post(`${bookApi}/cover`, {
      headers: staff,
      multipart: {
        file: {
          name: "portrait.png",
          mimeType: "image/png",
          buffer: Buffer.from(
            "iVBORw0KGgoAAAANSUhEUgAAABgAAAAoCAIAAABrb60CAAAAWUlEQVR42mMMTm1loAZgYqASoJpBLHDWlAIVMvTnTLiDbhCyKJEA2e7BF0Y0CGxcnscTwIQNIjXUh3dgjxo0atCoQaMGjRo0atBgq/vJa2uhG0RGfT+4wwgAnKcPcco66q8AAAAASUVORK5CYII=",
            "base64",
          ),
        },
      },
    });
    expect(uploaded.status()).toBe(200);
    const { cover_url } = await uploaded.json();
    await pageLogin(page, reader.email, reader.password, /\/dashboard$/);
    await page.goto(`/books/${id}`);
    const url = page.url();
    const source = page.getByRole("img", { name: title, exact: true });
    await source.evaluate((image: HTMLImageElement) => image.decode());
    const target = page.locator("[data-favorites-target]");
    const flight = page.locator("img[data-favorite-flight]");
    const add = page.getByRole("button", {
      name: "Таңдаулыға қосу",
      exact: true,
    });
    const remove = page.getByRole("button", {
      name: "Таңдаулыдан алып тастау",
      exact: true,
    });
    // Observe even short-lived copies while the real mutation's queries refetch.
    const flights = await page.evaluateHandle(() => {
      const distances: number[] = [];
      new MutationObserver((records) => {
        for (const record of records)
          for (const node of record.addedNodes)
            if (
              node instanceof HTMLImageElement &&
              node.hasAttribute("data-favorite-flight")
            ) {
              const effect = node
                .getAnimations()
                .find((a) => a.playState === "running")?.effect;
              const frames =
                effect instanceof KeyframeEffect ? effect.getKeyframes() : [];
              const start = new DOMMatrix(
                String(frames[0]?.transform ?? "none"),
              );
              const end = new DOMMatrix(
                String(frames.at(-1)?.transform ?? "none"),
              );
              distances.push(
                Math.hypot(end.m41 - start.m41, end.m42 - start.m42),
              );
            }
      }).observe(document.body, { childList: true, subtree: true });
      return distances;
    });
    let expected = 0;
    for (const mode of [
      "desktop",
      "mobile clipped",
      "mobile visible",
      "mobile scrolled",
      "reduced",
    ]) {
      await test.step(mode, async () => {
        const mobile = mode.startsWith("mobile");
        await page.setViewportSize(
          mobile ? { width: 390, height: 844 } : { width: 1280, height: 800 },
        );
        await page.emulateMedia({
          reducedMotion: mode === "reduced" ? "reduce" : "no-preference",
        });
        if (mode === "mobile visible" || mode === "mobile scrolled")
          await target.scrollIntoViewIfNeeded();
        if (mode === "mobile scrolled")
          await page.evaluate(() => scrollTo(0, 140));
        if (mode === "reduced") await page.evaluate(() => scrollTo(0, 0));
        const visible = mode !== "mobile clipped" && mode !== "mobile scrolled";
        if (visible) await expect(target).toBeInViewport({ ratio: 1 });
        else await expect(target).not.toBeInViewport();
        await expect(add).toBeEnabled();
        const scrollPosition = () =>
          target.evaluate((a) => [
            scrollX,
            scrollY,
            a.closest("nav")!.scrollLeft,
          ]);
        const before = await scrollPosition();
        // Keep the real POST pending while the reader moves focus elsewhere.
        const gate = Promise.withResolvers<void>();
        try {
          await page.route(
            `**/api/v1/favorites/${id}`,
            async (route) => {
              await gate.promise;
              await route.continue();
            },
            { times: 1 },
          );
          await add.click();
          await expect(add).toBeDisabled();
          await page
            .getByRole("heading", { level: 1 })
            .evaluate((h) => h.focus({ preventScroll: true }));
        } finally {
          gate.resolve();
        }
        if (visible && mode !== "reduced") {
          expected++;
          await expect(flight).toHaveAttribute(
            "src",
            new RegExp(cover_url + "$"),
          );
        }
        await expect(remove).toBeEnabled();
        await expect(flight).toHaveCount(0);
        const distances = await flights.jsonValue();
        expect(distances).toHaveLength(expected);
        if (visible && mode !== "reduced")
          expect(distances.at(-1)).toBeGreaterThan(20);
        expect(page.url()).toBe(url);
        expect(await scrollPosition()).toEqual(before);
        await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
        await expect(source).toBeVisible();
        if (mode !== "reduced") {
          await remove.click();
          await expect(add).toBeEnabled();
          expect(await flights.jsonValue()).toHaveLength(expected);
        }
      });
    }
    await page.goto("/favorites");
    const saved = page.getByRole("link", { name: title, exact: true });
    await expect(saved).toBeVisible();
    await remove.click();
    await expect(saved).toHaveCount(0);
  } finally {
    await request.delete(`/api/v1/favorites/${id}`, {
      headers: reader.headers,
    });
    await request.delete(`${bookApi}/cover`, { headers: staff });
    expect(
      (
        await request.patch(`${bookApi}/archive`, {
          headers: staff,
          data: { archived: true },
        })
      ).ok(),
    ).toBe(true);
  }
});
