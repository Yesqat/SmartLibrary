"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  CatalogShell,
  Failure,
  Field,
  inputClass,
} from "@/features/catalog/shared";
import { admin as t } from "@/locales/admin";
import { adminApi, type Setting } from "./api";
function SettingsForm({ rows: initial }: { rows: Setting[] }) {
  const [rows, setRows] = useState(initial);
  const [values, setValues] = useState<Record<string, number | boolean>>(() =>
    Object.fromEntries(rows.map((row) => [row.key, row.value])),
  );
  const cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      adminApi.saveSettings(
        rows
          .filter((row) => row.value !== values[row.key])
          .map((row) => ({
            key: row.key,
            value: values[row.key],
            expected_updated_at: row.updated_at,
          })),
      ),
    onSuccess: async (data) => {
      setRows(data);
      cache.setQueryData(["admin-settings"], data);
      await Promise.all(
        ["readers", "reader-summary", "librarian-dashboard", "audit-logs"].map(
          (key) => cache.invalidateQueries({ queryKey: [key] }),
        ),
      );
    },
  });
  const changed = rows.some((row) => row.value !== values[row.key]);
  return (
    <form
      className="max-w-2xl space-y-5"
      onSubmit={(e) => {
        e.preventDefault();
        if (changed && window.confirm(t.confirmSettings)) mutation.mutate();
      }}
    >
      <fieldset disabled={mutation.isPending} className="space-y-5">
        {rows.map((row) => (
          <Field
            key={row.key}
            label={
              t.settingLabels[row.key as keyof typeof t.settingLabels] ??
              row.key
            }
          >
            {row.value_type === "BOOLEAN" ? (
              <input
                type="checkbox"
                checked={Boolean(values[row.key])}
                onChange={(e) =>
                  setValues({ ...values, [row.key]: e.target.checked })
                }
                className="size-5"
              />
            ) : (
              <input
                className={inputClass}
                type="number"
                required
                step={1}
                min={row.minimum ?? undefined}
                max={row.maximum ?? undefined}
                value={
                  Number.isNaN(Number(values[row.key]))
                    ? ""
                    : Number(values[row.key])
                }
                onChange={(e) =>
                  setValues({ ...values, [row.key]: e.target.valueAsNumber })
                }
              />
            )}
          </Field>
        ))}
        <Button disabled={!changed} type="submit">
          {t.save}
        </Button>
      </fieldset>
      {mutation.isError && <Failure error={mutation.error} />}
      {mutation.isSuccess && <p role="status">{t.saved}</p>}
    </form>
  );
}
export function Settings() {
  const [revision, setRevision] = useState(0);
  const result = useQuery({
    queryKey: ["admin-settings"],
    queryFn: adminApi.settings,
    refetchOnWindowFocus: false,
  });
  return (
    <CatalogShell title={t.settings}>
      <p className="mb-6 max-w-2xl">{t.settingsHint}</p>
      {result.isPending ? (
        <p role="status">{t.loading}</p>
      ) : result.isError ? (
        <Failure error={result.error} retry={() => void result.refetch()} />
      ) : (
        <>
          <SettingsForm key={revision} rows={result.data} />
          <Button
            className="mt-5"
            variant="outline"
            onClick={async () => {
              if (
                window.confirm(
                  "Енгізілген өзгерістерді тастап, қайта жүктейсіз бе?",
                )
              ) {
                await result.refetch();
                setRevision((value) => value + 1);
              }
            }}
          >
            {t.updated}
          </Button>
        </>
      )}
    </CatalogShell>
  );
}
