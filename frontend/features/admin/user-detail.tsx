"use client";
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
import { useAuth } from "@/features/auth/auth-provider";
import { checkSession, type User } from "@/services/api-client";
import { admin as t } from "@/locales/admin";
import { adminApi } from "./api";
function AccountForm({ user }: { user: User }) {
  const [role, setRole] = useState(user.role),
    [status, setStatus] = useState(user.status);
  const auth = useAuth(),
    cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: (kind: "role" | "status") =>
      kind === "role"
        ? adminApi.role(user.id, role)
        : adminApi.status(user.id, status),
    onSuccess: async (data) => {
      cache.setQueryData(["admin-users", user.id], data);
      await Promise.all(
        ["admin-users", "admin-dashboard", "audit-logs", "readers"].map((key) =>
          cache.invalidateQueries({ queryKey: [key] }),
        ),
      );
      if (data.id === auth.user?.id) await checkSession();
    },
  });
  const submit = (kind: "role" | "status") => {
    if (window.confirm(t.confirm)) mutation.mutate(kind);
  };
  return (
    <fieldset disabled={mutation.isPending} className="mt-6 space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <Field label={t.role}>
          <select
            value={role}
            className={inputClass}
            onChange={(e) => setRole(e.target.value as User["role"])}
          >
            {Object.entries(t.roles).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Button disabled={role === user.role} onClick={() => submit("role")}>
          {t.changeRole}
        </Button>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <Field label={t.status}>
          <select
            value={status}
            className={inputClass}
            onChange={(e) => setStatus(e.target.value as User["status"])}
          >
            {Object.entries(t.statuses).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Button
          disabled={status === user.status}
          onClick={() => submit("status")}
        >
          {t.changeStatus}
        </Button>
      </div>
      {mutation.isError && <Failure error={mutation.error} />}
      {mutation.isSuccess && <p role="status">{t.changed}</p>}
    </fieldset>
  );
}
export function UserDetail({ id }: { id: string }) {
  const result = useQuery({
    queryKey: ["admin-users", id],
    queryFn: () => adminApi.user(id),
  });
  return (
    <CatalogShell title={t.user}>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          <h2 className="text-xl font-semibold">
            {result.data.first_name} {result.data.last_name}
          </h2>
          <p>{result.data.email}</p>
          <p>{result.data.phone ?? ""}</p>
          <p className="mt-2 text-sm">ID: {result.data.id}</p>
          <AccountForm user={result.data} />
          <div className="mt-8 flex flex-wrap gap-5">
            <Link
              className="text-primary underline"
              href={`/admin/borrowings?user_id=${id}`}
            >
              {t.borrowings}
            </Link>
            <Link
              className="text-primary underline"
              href={`/admin/reservations?user_id=${id}`}
            >
              {t.reservations}
            </Link>
          </div>
        </>
      )}
    </CatalogShell>
  );
}
