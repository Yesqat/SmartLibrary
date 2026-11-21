"use client";

import Link from "next/link";
import { KeyRound, MonitorSmartphone } from "lucide-react";
import styles from "./account.module.css";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { kk } from "@/locales/kk";
import {
  ApiError,
  apiRequest,
  changePassword,
  revokeSession,
  type Session,
} from "@/services/api-client";
import { useAuth } from "./auth-provider";
import { inputClass } from "./auth-form";
import { homeForRole } from "./navigation";

export function SecurityPanel() {
  const { user } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const sessions = useQuery({
    queryKey: ["auth-sessions", user?.id],
    queryFn: () => apiRequest<Session[]>("/auth/sessions"),
    enabled: !!user,
    retry: false,
  });
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    setError("");
    setMessage("");
    if (data.get("new_password") !== data.get("confirm")) {
      setError(kk.auth.mismatch);
      return;
    }
    setBusy(true);
    try {
      await changePassword({
        current_password: String(data.get("current_password")),
        new_password: String(data.get("new_password")),
      });
      form.reset();
      router.replace("/login?changed=1");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : kk.error);
    } finally {
      setBusy(false);
    }
  }
  const date = (value: string) =>
    new Intl.DateTimeFormat("kk-KZ", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "UTC",
    }).format(new Date(value)) + " UTC";
  return (
    <main className={styles.account}>
      <Link
        className="text-primary underline"
        href={user ? homeForRole(user.role) : "/login"}
      >
        {kk.auth.back}
      </Link>
      <h1 className="mt-8 text-3xl font-semibold">{kk.auth.security}</h1>
      <p className="mt-3 text-muted-foreground">
        {kk.auth.securityDescription}
      </p>
      <section className="mt-8 rounded-2xl border border-border p-6">
        <h2 className="text-xl font-semibold">
          <KeyRound aria-hidden="true" />
          {kk.auth.passwordChange}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {kk.auth.passwordWarning}
        </p>
        <form className="mt-6 space-y-5" onSubmit={submit} aria-busy={busy}>
          <label className="block">
            {kk.auth.currentPassword} *
            <input
              name="current_password"
              type="password"
              autoComplete="current-password"
              required
              maxLength={128}
              className={inputClass}
              disabled={busy}
            />
          </label>
          <label className="block">
            {kk.auth.newPassword} *
            <input
              name="new_password"
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={128}
              className={inputClass}
              disabled={busy}
              aria-describedby="new-password-hint"
            />
          </label>
          <p id="new-password-hint" className="text-sm text-muted-foreground">
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
          <Button type="submit" disabled={busy}>
            {busy ? kk.auth.pending : kk.auth.passwordChange}
          </Button>
        </form>
      </section>
      {error && (
        <p
          role="alert"
          className="mt-4 rounded-xl bg-destructive/10 p-4 text-destructive"
        >
          {error}
        </p>
      )}
      {message && (
        <p role="status" className="mt-4">
          {message}
        </p>
      )}
      <section className="mt-8 rounded-2xl border border-border p-6">
        <h2 className="text-xl font-semibold">
          <MonitorSmartphone aria-hidden="true" />
          {kk.auth.sessions}
        </h2>
        {sessions.isPending && (
          <p role="status" className="mt-4">
            {kk.auth.loading}
          </p>
        )}
        {sessions.isError && (
          <div role="alert" className="mt-4">
            <p>
              {sessions.error instanceof ApiError
                ? sessions.error.message
                : kk.error}
            </p>
            <Button
              variant="outline"
              className="mt-3"
              onClick={() => void sessions.refetch()}
            >
              {kk.auth.retry}
            </Button>
          </div>
        )}
        {sessions.data?.length === 0 && (
          <p className="mt-4">{kk.auth.noSessions}</p>
        )}
        <ul className="mt-4 space-y-4">
          {sessions.data?.map((session) => (
            <li key={session.id} className="rounded-xl bg-muted p-4">
              <h3 className="font-semibold">
                {session.current
                  ? kk.auth.currentSession
                  : kk.auth.otherSession}
              </h3>
              <p className="mt-2 text-sm">
                {kk.auth.sessionCreated}: {date(session.created_at)}
              </p>
              <p className="text-sm">
                {kk.auth.expires}: {date(session.expires_at)}
              </p>
              <Button
                className="mt-3"
                variant="outline"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  setMessage("");
                  try {
                    await revokeSession(session);
                    setMessage(kk.auth.revoked);
                    if (!session.current) await sessions.refetch();
                  } catch (cause) {
                    setError(
                      cause instanceof ApiError ? cause.message : kk.error,
                    );
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {kk.auth.revoke}
              </Button>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
