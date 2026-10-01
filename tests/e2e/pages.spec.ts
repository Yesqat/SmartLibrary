import { randomUUID } from "node:crypto";
import {
  test,
  expect,
  type Page,
  type Request,
} from "../../frontend/node_modules/@playwright/test";
import { apiLogin, apiReader, pageLogin } from "./library-helpers";

test.use({ trace: "off", video: "off", screenshot: "off" });

async function visit(page: Page, paths: string[]) {
  const pending = new Set<Request>();
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/")) pending.add(request);
  });
  page.on("requestfinished", (request) => pending.delete(request));
  page.on("requestfailed", (request) => pending.delete(request));
  page.on("response", (response) => {
    if (
      response.url().includes("/api/v1/") &&
      response.status() >= 400 &&
      !response.url().endsWith("/auth/refresh")
    ) {
      errors.push(`${response.status()} ${new URL(response.url()).pathname}`);
    }
  });
  for (const path of paths) {
    expect((await page.goto(path))?.status()).toBe(200);
    await expect(page).toHaveURL((url) => url.pathname === path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(
      page.getByRole("status").filter({ hasText: /жүктел/i }),
    ).toHaveCount(0);
    await expect.poll(() => pending.size).toBe(0);
    // Next.js keeps a route-announcement alert outside the application landmark.
    await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
    expect(errors).toEqual([]);
    console.log(
      `Verified rendered page ${path.replace(/[a-f0-9]{8}-[a-f0-9-]{27}/g, "{id}")}`,
    );
  }
}

for (const role of ["PUBLIC", "READER", "LIBRARIAN", "ADMIN"] as const) {
  test(`final ${role} page and real API review`, async ({ page, request }) => {
    test.setTimeout(300000);
    const password = process.env.E2E_SEED_PASSWORD;
    if (!password) throw new Error("E2E_SEED_PASSWORD required");
    const staff = await apiLogin(
      request,
      "librarian@smartlibrary.example",
      password,
    );
    const created = await request.post("/api/v1/books", {
      headers: staff,
      data: { title: `Беттерді тексеру ${randomUUID()}`, language: "kk" },
    });
    expect(created.status()).toBe(201);
    const book = await created.json();
    let reservation: string | undefined;
    let owner: Record<string, string> | undefined;
    try {
      if (role === "PUBLIC") {
        await visit(page, [
          "/",
          "/catalog",
          `/books/${book.id}`,
          "/login",
          "/register",
        ]);
      } else {
        const reader = await apiReader(request);
        if (role === "READER") {
          expect(
            (
              await request.post(`/api/v1/books/${book.id}/copies`, {
                headers: staff,
                data: { inventory_number: `PAGE-${randomUUID()}` },
              })
            ).status(),
          ).toBe(201);
          const reserved = await request.post("/api/v1/reservations", {
            headers: reader.headers,
            data: { book_id: book.id },
          });
          expect(reserved.status()).toBe(201);
          reservation = (await reserved.json()).id;
          owner = reader.headers;
          await pageLogin(page, reader.email, reader.password, /\/dashboard$/);
          await visit(page, [
            "/dashboard",
            "/catalog",
            `/books/${book.id}`,
            "/assistant",
            "/favorites",
            "/reservations",
            `/reservations/${reservation}`,
            "/my-books",
            "/history",
            "/notifications",
            "/account/profile",
            "/account/security",
          ]);
        } else {
          const root = role === "ADMIN" ? "/admin" : "/librarian";
          await pageLogin(
            page,
            `${role.toLowerCase()}@smartlibrary.example`,
            password,
            new RegExp(`${root}$`),
          );
          const common = [
            root,
            `${root}/books`,
            `${root}/books/new`,
            `${root}/books/${book.id}`,
            `${root}/books/${book.id}/copies`,
            `${root}/references`,
            `${root}/reservations`,
            `${root}/category-predictions`,
            "/account/profile",
            "/account/security",
          ];
          await visit(page, [
            ...common,
            ...(role === "ADMIN"
              ? [
                  "/admin/users",
                  `/admin/users/${reader.user.id}`,
                  "/admin/librarians",
                  "/admin/authors",
                  "/admin/categories",
                  "/admin/publishers",
                  "/admin/inventory",
                  "/admin/borrowings",
                  "/admin/analytics",
                  "/admin/reports",
                  "/admin/ai",
                  "/admin/settings",
                  "/admin/audit-logs",
                ]
              : [
                  "/librarian/qr",
                  "/librarian/issue",
                  "/librarian/return",
                  "/librarian/readers",
                  `/librarian/readers/${reader.user.id}`,
                  "/librarian/overdue",
                ]),
          ]);
        }
      }
    } finally {
      if (reservation)
        expect(
          (
            await request.post(`/api/v1/reservations/${reservation}/cancel`, {
              headers: owner,
            })
          ).status(),
        ).toBe(200);
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
}
