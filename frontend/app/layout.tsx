import type { Metadata } from "next";
import { connection } from "next/server";
import { kk } from "@/locales/kk";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: kk.name,
  description: kk.description,
};
export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // Request rendering lets Next apply this response's CSP nonce to hydration scripts.
  await connection();
  return (
    <html lang="kk">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
