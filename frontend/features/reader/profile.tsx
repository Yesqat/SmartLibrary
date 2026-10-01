"use client";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  CatalogShell,
  Failure,
  Field,
  inputClass,
} from "@/features/catalog/shared";
import { ReferencePicker } from "@/features/catalog/reference-picker";
import type { Reference } from "@/features/catalog/api";
import { checkSession, type User } from "@/services/api-client";
import { reader as t } from "@/locales/reader";
import { readerApi, type Preferences } from "./api";

function ProfileForm({ user }: { user: User }) {
  const cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: readerApi.saveProfile,
    onSuccess: async (data) => {
      cache.setQueryData(["profile"], data);
      await checkSession();
    },
  });
  return (
    <form
      className="grid gap-5"
      onSubmit={(e) => {
        e.preventDefault();
        const form = new FormData(e.currentTarget);
        mutation.mutate({
          first_name: String(form.get("first_name")),
          last_name: String(form.get("last_name")),
          phone: String(form.get("phone")) || null,
        });
      }}
    >
      <fieldset className="grid gap-5" disabled={mutation.isPending}>
        <Field label={t.firstName}>
          <input
            className={inputClass}
            name="first_name"
            defaultValue={user.first_name}
            required
            maxLength={100}
            autoComplete="given-name"
          />
        </Field>
        <Field label={t.lastName}>
          <input
            className={inputClass}
            name="last_name"
            defaultValue={user.last_name}
            required
            maxLength={100}
            autoComplete="family-name"
          />
        </Field>
        <Field label={t.phone}>
          <input
            className={inputClass}
            name="phone"
            defaultValue={user.phone ?? ""}
            type="tel"
            maxLength={32}
            autoComplete="tel"
          />
        </Field>
        <Button type="submit">{t.save}</Button>
      </fieldset>
      {mutation.isError && <Failure error={mutation.error} />}
      {mutation.isSuccess && <p role="status">{t.saved}</p>}
    </form>
  );
}
function Avatar({ user }: { user: User }) {
  const cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: readerApi.avatar,
    onSuccess: async (data) => {
      cache.setQueryData(["profile"], data);
      await checkSession();
    },
  });
  return (
    <section className="mb-8 rounded-xl border p-5">
      <h2 className="mb-4 text-xl font-semibold">{t.avatar}</h2>
      {user.avatar_url ? (
        <Image
          src={user.avatar_url}
          width={96}
          height={96}
          unoptimized
          className="size-24 rounded-full object-cover"
          alt={t.avatar}
        />
      ) : (
        <div
          aria-label={t.avatar}
          className="flex size-24 items-center justify-center rounded-full bg-emerald-100 text-3xl"
        >
          {user.first_name[0]}
          {user.last_name[0]}
        </div>
      )}
      <p className="my-3 text-sm">{t.imageHint}</p>
      <form
        className="flex flex-wrap gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          const file = new FormData(e.currentTarget).get("file");
          if (file instanceof File && file.size) mutation.mutate(file);
        }}
      >
        <input
          aria-label={t.avatar}
          name="file"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          required
          disabled={mutation.isPending}
        />
        <Button type="submit" disabled={mutation.isPending}>
          {t.upload}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={mutation.isPending || !user.avatar_url}
          onClick={() => {
            if (window.confirm(t.confirmRemove)) mutation.mutate(null);
          }}
        >
          {t.removeAvatar}
        </Button>
      </form>
      {mutation.isError && <Failure error={mutation.error} />}
      {mutation.isSuccess && <p role="status">{t.saved}</p>}
    </section>
  );
}
function PreferenceForm({ initial }: { initial: Preferences }) {
  const [selected, setSelected] = useState<Reference[]>(initial.categories);
  const cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => readerApi.savePreferences(selected.map((row) => row.id)),
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["preferences"] });
      await cache.invalidateQueries({ queryKey: ["recommendations"] });
    },
  });
  return (
    <fieldset disabled={mutation.isPending} className="space-y-4">
      <p className="text-sm">{t.optional}</p>
      <ReferencePicker
        kind="categories"
        selected={selected}
        onChange={(rows) => {
          if (rows.length <= 30) setSelected(rows);
        }}
      />
      <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
        {t.save}
      </Button>
      {mutation.isError && <Failure error={mutation.error} />}
      {mutation.isSuccess && <p role="status">{t.saved}</p>}
    </fieldset>
  );
}
function Interests() {
  const result = useQuery({
    queryKey: ["preferences"],
    queryFn: readerApi.preferences,
  });
  return (
    <section className="mt-8 rounded-xl border p-5">
      <h2 className="mb-4 text-xl font-semibold">{t.preferences}</h2>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <PreferenceForm initial={result.data} />
      )}
    </section>
  );
}
export function Profile() {
  const result = useQuery({
    queryKey: ["profile"],
    queryFn: readerApi.profile,
  });
  return (
    <CatalogShell title={t.profile}>
      <div className="max-w-2xl">
        {result.isPending ? (
          <p role="status">{t.loading}</p>
        ) : result.isError ? (
          <Failure error={result.error} retry={() => void result.refetch()} />
        ) : (
          <>
            <p>
              {t.email}: {result.data.email}
            </p>
            <p className="my-4 text-sm text-muted-foreground">
              {t.emailPolicy}
            </p>
            <Avatar user={result.data} />
            <ProfileForm user={result.data} />
            {result.data.role === "READER" && <Interests />}
            <Link
              className="mt-6 inline-block text-primary underline"
              href="/account/security"
            >
              {t.security}
            </Link>
          </>
        )}
      </div>
    </CatalogShell>
  );
}
