"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  CatalogShell,
  Failure,
  Field,
  inputClass,
} from "@/features/catalog/shared";
import { reports as t } from "@/locales/reports";
import { reportsApi, type ReportInput } from "./api";
import type { Download } from "@/services/api-client";
function DownloadLink({ data }: { data: Download }) {
  const anchor = useRef<HTMLAnchorElement>(null);
  useEffect(() => {
    const url = URL.createObjectURL(data.blob);
    if (anchor.current) anchor.current.href = url;
    return () => URL.revokeObjectURL(url);
  }, [data]);
  return (
    <Button asChild className="mt-4">
      <a ref={anchor} download={data.filename}>
        {t.download}
      </a>
    </Button>
  );
}
export function ReportsPage() {
  const [values, setValues] = useState<ReportInput>({
    report_type: "inventory",
    format: "pdf",
  });
  const result = useMutation({ mutationFn: reportsApi.generate });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!result.isPending) {
      result.reset();
      result.mutate(values);
    }
  }
  return (
    <CatalogShell title={t.title}>
      <p className="mb-4">{t.note}</p>
      <p className="mb-5 text-sm text-muted-foreground">{t.private}</p>
      <form
        className="grid gap-5 rounded-xl border p-5 sm:grid-cols-2"
        onSubmit={submit}
        aria-busy={result.isPending}
      >
        <Field label={t.type}>
          <select
            className={inputClass}
            value={values.report_type}
            disabled={result.isPending}
            onChange={(e) =>
              setValues({
                ...values,
                report_type: e.target.value as ReportInput["report_type"],
              })
            }
          >
            {Object.entries(t.types).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t.format}>
          <select
            className={inputClass}
            value={values.format}
            disabled={result.isPending}
            onChange={(e) =>
              setValues({
                ...values,
                format: e.target.value as ReportInput["format"],
              })
            }
          >
            <option value="pdf">PDF</option>
            <option value="xlsx">XLSX</option>
          </select>
        </Field>
        <Field label={t.from}>
          <input
            type="date"
            className={inputClass}
            min="1900-01-01"
            max={values.date_to || "9998-12-31"}
            disabled={result.isPending}
            value={values.date_from ?? ""}
            onChange={(e) =>
              setValues({ ...values, date_from: e.target.value || null })
            }
          />
        </Field>
        <Field label={t.to}>
          <input
            type="date"
            className={inputClass}
            min={values.date_from || "1900-01-01"}
            max="9998-12-31"
            disabled={result.isPending}
            value={values.date_to ?? ""}
            onChange={(e) =>
              setValues({ ...values, date_to: e.target.value || null })
            }
          />
        </Field>
        <Button disabled={result.isPending}>
          {result.isPending ? t.generating : t.generate}
        </Button>
      </form>
      {result.isError && <Failure error={result.error} />}
      {result.isSuccess && (
        <section className="mt-6 rounded-xl border bg-emerald-50 p-5">
          <p role="status">
            {t.ready}. {t.rows}: {result.data.rows}
          </p>
          {result.data.rows === 0 && <p className="my-3">{t.empty}</p>}
          <DownloadLink data={result.data} />
          <p className="mt-2 break-all text-sm">{result.data.filename}</p>
        </section>
      )}
    </CatalogShell>
  );
}
