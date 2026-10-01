"use client";
import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  CatalogShell,
  Failure,
  Field,
  inputClass,
} from "@/features/catalog/shared";
import { circulation as t } from "@/locales/circulation";
import { circulationApi, type PickupPreview } from "./api";
import { librarianApi } from "@/features/librarian/api";
import { librarian as lt } from "@/locales/librarian";
import { CameraScanner } from "./camera-scanner";

function PickupConfirmation({
  preview,
  onIssued,
}: {
  preview: PickupPreview;
  onIssued: () => void;
}) {
  const [expired, setExpired] = useState(
    () => Date.parse(preview.verification_expires_at) <= Date.now(),
  );
  const cache = useQueryClient();
  useEffect(() => {
    const timer = window.setTimeout(
      () => setExpired(true),
      Math.max(0, Date.parse(preview.verification_expires_at) - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [preview.verification_expires_at]);
  const issue = useMutation({
    mutationFn: () =>
      circulationApi.issueReserved(
        preview.reservation_id,
        preview.verification_token,
      ),
    onSuccess: async () => {
      await Promise.all(
        [
          "catalog",
          "recommendations",
          "search",
          "favorites",
          "reader-summary",
          "reservations",
          "borrowings",
        ].map((key) => cache.invalidateQueries({ queryKey: [key] })),
      );
      onIssued();
    },
  });
  return (
    <section className="mt-8 rounded-xl border bg-white p-6">
      <p role="status" className="font-semibold">
        {issue.isSuccess ? t.issued : t.verified}
      </p>
      <dl className="my-6 grid gap-5 sm:grid-cols-2">
        {[
          [t.reader, preview.reader_name],
          [lt.number, preview.reservation_number],
          [lt.status, issue.isSuccess ? "Аяқталған" : "Алуға дайын"],
          [t.book, preview.book_title],
          [t.inventory, preview.inventory_number],
          ["Сөре", preview.shelf_location ?? "—"],
          [t.deadline, new Date(preview.expires_at).toLocaleString("kk-KZ")],
        ].map(([label, value]) => (
          <div key={label}>
            <dt className="text-sm text-muted-foreground">{label}</dt>
            <dd className="mt-1 font-medium">{value}</dd>
          </div>
        ))}
      </dl>
      {issue.isSuccess ? (
        <p>
          {t.due}: {new Date(issue.data.due_at).toLocaleString("kk-KZ")}
        </p>
      ) : (
        <>
          {expired && <p role="alert">{t.reverify}</p>}
          {issue.isError && <Failure error={issue.error} />}
          <Button
            disabled={issue.isPending || expired}
            onClick={() => {
              if (window.confirm(t.confirmation)) issue.mutate();
            }}
          >
            {issue.isPending ? t.pending : t.issue}
          </Button>
        </>
      )}
    </section>
  );
}

export function Pickup() {
  const [token, setToken] = useState("");
  const [number, setNumber] = useState("");
  const [preview, setPreview] = useState<PickupPreview | null>(null);
  const verify = useMutation({
    mutationFn: (input: { text: string; manual?: boolean }) =>
      input.manual
        ? librarianApi.manual(input.text)
        : circulationApi.verify(input.text),
    onSuccess: (value) => {
      setPreview(value);
      setToken("");
      setNumber("");
    },
  });
  return (
    <CatalogShell title={t.title}>
      <p className="mb-5 max-w-2xl">{t.instruction}</p>
      {!verify.isPending && (
        <CameraScanner
          onStart={() => {
            setPreview(null);
            verify.reset();
          }}
          onDecoded={(text) => {
            setPreview(null);
            verify.mutate({ text });
          }}
        />
      )}
      <form
        className="max-w-2xl space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setPreview(null);
          verify.mutate({ text: token.trim() });
        }}
      >
        <Field label={t.token}>
          <textarea
            className={inputClass}
            value={token}
            onChange={(e) => {
              setToken(e.target.value);
              setPreview(null);
            }}
            minLength={32}
            maxLength={256}
            required
            autoComplete="off"
            spellCheck={false}
            disabled={verify.isPending}
          />
        </Field>
        <Button disabled={verify.isPending}>
          {verify.isPending ? t.pending : t.verify}
        </Button>
      </form>
      <form
        className="mt-6 max-w-2xl space-y-4 rounded-xl border p-5"
        onSubmit={(e) => {
          e.preventDefault();
          setPreview(null);
          verify.mutate({ text: number.trim(), manual: true });
        }}
      >
        <h2 className="text-lg font-semibold">{lt.manual}</h2>
        <p className="text-sm">{lt.manualHint}</p>
        <Field label={lt.number}>
          <input
            className={inputClass}
            required
            minLength={3}
            maxLength={80}
            value={number}
            disabled={verify.isPending}
            onChange={(e) => {
              setNumber(e.target.value);
              setPreview(null);
            }}
          />
        </Field>
        <Button disabled={verify.isPending}>{lt.manual}</Button>
      </form>
      {verify.isError && <Failure error={verify.error} />}
      {preview && (
        <PickupConfirmation
          key={preview.verification_token}
          preview={preview}
          onIssued={() => setToken("")}
        />
      )}
    </CatalogShell>
  );
}
