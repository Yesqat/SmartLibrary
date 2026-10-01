"use client";

import Link from "next/link";
import Image from "next/image";
import { ArrowRight, BookOpen, LockKeyhole, Mail, Sprout } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { kk } from "@/locales/kk";
import { ApiError, login, register } from "@/services/api-client";
import { safeReturnTo } from "./navigation";
import loginBooks from "./assets/login-books.png";
import styles from "./login.module.css";

export const inputClass =
  "mt-2 block w-full rounded-xl border border-border bg-background px-4 py-3 outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-60";

export function AuthForm({
  mode,
  passwordChanged = false,
}: {
  mode: "login" | "register";
  passwordChanged?: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const registration = mode === "register";
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setError("");
    setSuccess("");
    const form = event.currentTarget;
    if (!form.reportValidity()) {
      setError(kk.auth.required);
      return;
    }
    const data = new FormData(form);
    const email = String(data.get("email") ?? "").trim();
    const password = String(data.get("password") ?? "");
    if (registration && password !== data.get("confirm")) {
      setError(kk.auth.mismatch);
      return;
    }
    setBusy(true);
    try {
      if (registration) {
        await register({
          email,
          password,
          first_name: String(data.get("first_name")),
          last_name: String(data.get("last_name")),
          phone: String(data.get("phone") || "") || null,
        });
        form.reset();
        setSuccess(kk.auth.registered);
      } else {
        const user = await login({ email, password });
        const next = new URLSearchParams(window.location.search).get("next");
        router.replace(safeReturnTo(next, user.role));
      }
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : kk.error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main
      className={
        registration
          ? "mx-auto grid min-h-screen max-w-6xl items-center gap-12 px-6 py-12 lg:grid-cols-2"
          : styles.login
      }
    >
      <section className={registration ? undefined : styles.intro}>
        <Link href="/" className="font-semibold tracking-widest text-primary">
          {!registration && <BookOpen aria-hidden="true" />}
          {kk.name}
        </Link>
        {!registration && <p className={styles.eyebrow}>SMARTLIBRARY</p>}
        <h1 className="mt-10 text-4xl font-semibold leading-tight">
          {registration ? kk.auth.registerTitle : kk.auth.loginTitle}
        </h1>
        <p className="mt-5 max-w-md text-lg text-muted-foreground">
          {registration
            ? kk.auth.registerDescription
            : kk.auth.loginDescription}
        </p>
        {!registration && (
          <div className={styles.illustration} aria-hidden="true">
            <Image
              src={loginBooks}
              alt=""
              width={1536}
              height={1024}
              sizes="(max-width: 767px) 1px, (max-width: 1099px) 440px, 760px"
              loading="eager"
            />
          </div>
        )}
      </section>
      <section
        className={
          registration
            ? "rounded-3xl border border-border bg-card p-6 shadow-sm sm:p-10"
            : styles.card
        }
      >
        {!registration && (
          <header className={styles.cardHeading}>
            <h2>Жүйеге кіру</h2>
            <p>SmartLibrary-ға қайта қош келдіңіз!</p>
          </header>
        )}
        {passwordChanged && (
          <p role="status" className="mb-6 rounded-xl bg-muted p-4">
            {kk.auth.passwordChanged}
          </p>
        )}
        {success ? (
          <div role="status">
            <p className="text-lg">{success}</p>
            <Button asChild className="mt-6">
              <Link href="/login">{kk.auth.login}</Link>
            </Button>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-5" aria-busy={busy}>
            {registration && (
              <div className="grid gap-5 sm:grid-cols-2">
                <label>
                  {kk.auth.firstName} *
                  <input
                    name="first_name"
                    autoComplete="given-name"
                    required
                    maxLength={100}
                    className={inputClass}
                    disabled={busy}
                  />
                </label>
                <label>
                  {kk.auth.lastName} *
                  <input
                    name="last_name"
                    autoComplete="family-name"
                    required
                    maxLength={100}
                    className={inputClass}
                    disabled={busy}
                  />
                </label>
              </div>
            )}
            <label className="block">
              {kk.auth.email} *{!registration && <Mail aria-hidden="true" />}
              <input
                name="email"
                type="email"
                autoComplete="email"
                required
                maxLength={320}
                className={inputClass}
                disabled={busy}
              />
            </label>
            {registration && (
              <label className="block">
                {kk.auth.phone}
                <input
                  name="phone"
                  type="tel"
                  autoComplete="tel"
                  maxLength={32}
                  className={inputClass}
                  disabled={busy}
                />
              </label>
            )}
            <label className="block">
              {kk.auth.password} *
              {!registration && <LockKeyhole aria-hidden="true" />}
              <input
                name="password"
                type="password"
                autoComplete={
                  registration ? "new-password" : "current-password"
                }
                required
                minLength={registration ? 12 : 1}
                maxLength={128}
                aria-describedby={registration ? "password-hint" : undefined}
                className={inputClass}
                disabled={busy}
              />
            </label>
            {registration && (
              <>
                <p id="password-hint" className="text-sm text-muted-foreground">
                  {kk.auth.passwordHint}
                </p>
                <label className="block">
                  {kk.auth.confirm} *
                  <input
                    name="confirm"
                    type="password"
                    autoComplete="new-password"
                    required
                    minLength={12}
                    maxLength={128}
                    className={inputClass}
                    disabled={busy}
                  />
                </label>
              </>
            )}
            {error && (
              <p
                role="alert"
                className="rounded-lg bg-destructive/10 p-3 text-destructive"
              >
                {error}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={busy}>
              {busy
                ? kk.auth.pending
                : registration
                  ? kk.auth.register
                  : kk.auth.login}
              {!registration && <ArrowRight aria-hidden="true" />}
            </Button>
            {!registration && (
              <div className={styles.divider} aria-hidden="true">
                Немесе
              </div>
            )}
            <p className="text-center text-sm">
              <Link
                className="underline underline-offset-4"
                href={registration ? "/login" : "/register"}
              >
                {registration ? kk.auth.login : kk.auth.register}
              </Link>
            </p>
          </form>
        )}
      </section>
      {!registration && (
        <aside className={styles.quote} aria-hidden="true">
          <Sprout />
          <p>Білім бүгін — жақсырақ ертең үшін</p>
        </aside>
      )}
    </main>
  );
}
