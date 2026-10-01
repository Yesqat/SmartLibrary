import { randomUUID } from "node:crypto";
import { test, expect } from "../../frontend/node_modules/@playwright/test";
import { apiLogin, apiReader, pageLogin } from "./library-helpers";
test.use({ trace: "off", video: "off", screenshot: "off" });
test("Librarian panel decodes a real QR from a controlled camera stream, previews and explicitly issues", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const password = process.env.E2E_SEED_PASSWORD;
  if (!password) throw new Error("E2E_SEED_PASSWORD required");
  const staff = await apiLogin(
    request,
    "librarian@smartlibrary.example",
    password,
  );
  const created = await request.post("/api/v1/books", {
    headers: staff,
    data: { title: `Кітапханашы тексеруі ${randomUUID()}`, language: "kk" },
  });
  expect(created.status()).toBe(201);
  const book = await created.json();
  const copyResponse = await request.post(`/api/v1/books/${book.id}/copies`, {
    headers: staff,
    data: { inventory_number: `CAM-${randomUUID()}`, shelf_location: "CAM-1" },
  });
  expect(copyResponse.status()).toBe(201);
  const copy = await copyResponse.json();
  const reader = await apiReader(request);
  const reserved = await request.post("/api/v1/reservations", {
    headers: reader.headers,
    data: { book_id: book.id },
  });
  expect(reserved.status()).toBe(201);
  const reservation = await reserved.json();
  let loanId: string | undefined;
  try {
    const credential = await request.get(
      `/api/v1/reservations/${reservation.id}/qr`,
      { headers: reader.headers },
    );
    expect(credential.status()).toBe(200);
    const qr = (await credential.json()).image_data_url;
    // Only the unavailable physical camera is substituted; actual QR pixels,
    // ZXing decoding, backend verification and issue transaction remain real.
    await page.addInitScript(
      ({ qr }) => {
        Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
          configurable: true,
          value: async () => {
            const canvas = document.createElement("canvas");
            canvas.width = 640;
            canvas.height = 480;
            const ctx = canvas.getContext("2d")!;
            const image = new Image();
            await new Promise<void>((resolve, reject) => {
              image.onload = () => resolve();
              image.onerror = () =>
                reject(new Error("QR fixture image failed"));
              image.src = qr;
            });
            const draw = () => {
              ctx.fillStyle = "white";
              ctx.fillRect(0, 0, 640, 480);
              ctx.drawImage(image, 100, 20, 440, 440);
            };
            draw();
            const stream = canvas.captureStream(10);
            const timer = setInterval(() => {
              if (stream.active) draw();
              else clearInterval(timer);
            }, 100);
            return stream;
          },
        });
      },
      { qr },
    );
    await pageLogin(
      page,
      "librarian@smartlibrary.example",
      password,
      /\/librarian$/,
    );
    await expect(
      page.getByText("Бүгін берілген", { exact: true }),
    ).toBeVisible();
    await page.goto("/librarian/readers");
    await page.getByLabel("Аты, email немесе ID").fill(reader.email);
    await page.getByRole("button", { name: "Іздеу", exact: true }).click();
    await page
      .getByRole("link", { name: "Оқырман Тексеру", exact: true })
      .click();
    await expect(page.getByText(/Қолдағы кітаптар \/ лимит/)).toBeVisible();
    await page.goto("/librarian/qr");
    let issues = 0;
    page.on("request", (r) => {
      if (
        r.method() === "POST" &&
        r.url().endsWith(`/reservations/${reservation.id}/issue`)
      )
        issues++;
    });
    await page
      .getByRole("button", { name: "Камерамен сканерлеу", exact: true })
      .click();
    await expect(
      page.getByText("Бронь тексерілді. Кітап әлі берілген жоқ.", {
        exact: true,
      }),
    ).toBeVisible({ timeout: 20000 });
    expect(issues).toBe(0);
    expect(
      (
        await (
          await request.get(
            `/api/v1/librarian/borrowings/by-inventory/${copy.inventory_number}`,
            { headers: staff },
          )
        ).json()
      ).active_borrowing,
    ).toBeNull();
    await page
      .getByLabel("Бронь нөмірі", { exact: true })
      .fill(reservation.reservation_number);
    await page
      .getByRole("button", { name: "Бронь нөмірімен тексеру", exact: true })
      .click();
    await expect(
      page.getByText("Бронь тексерілді. Кітап әлі берілген жоқ.", {
        exact: true,
      }),
    ).toBeVisible();
    expect(issues).toBe(0);
    page.once("dialog", (dialog) => dialog.accept());
    const issued = page.waitForResponse(
      (r) =>
        r.request().method() === "POST" &&
        r.url().endsWith(`/reservations/${reservation.id}/issue`),
    );
    await page
      .getByRole("button", { name: "Кітапты беру", exact: true })
      .click();
    const response = await issued;
    expect(response.status()).toBe(200);
    loanId = (await response.json()).id;
    expect(issues).toBe(1);
    await page.goto("/librarian/reservations");
    await page
      .getByLabel("Нөмір, кітап немесе оқырман")
      .fill(reservation.reservation_number);
    await page.getByRole("button", { name: "Іздеу", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: book.title, exact: true }),
    ).toBeVisible();
    await page.goto("/librarian/overdue");
    await expect(
      page.getByRole("heading", {
        name: "Мерзімі өткен кітаптар",
        exact: true,
      }),
    ).toBeVisible();
  } finally {
    if (loanId)
      expect(
        (
          await request.post(`/api/v1/librarian/borrowings/${loanId}/return`, {
            headers: staff,
            data: { condition: "GOOD" },
          })
        ).status(),
      ).toBe(200);
    else
      await request.post(`/api/v1/reservations/${reservation.id}/cancel`, {
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
