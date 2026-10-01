"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Failure } from "@/features/catalog/shared";
import { ReferencePicker } from "@/features/catalog/reference-picker";
import type { Reference } from "@/features/catalog/api";
import { categorization as t } from "@/locales/categorization";
import { categorizationApi, type PredictionRun } from "./api";

export function PredictionReview({ run }: { run: PredictionRun }) {
  const [selected, setSelected] = useState(
    run.predictions.map((row) => row.category_id),
  );
  const [manual, setManual] = useState<Reference[]>([]);
  const cache = useQueryClient();
  const save = useMutation({
    mutationFn: () =>
      categorizationApi.review(run.id, [
        ...new Set([...selected, ...manual.map((row) => row.id)]),
      ]),
    onSuccess: async () => {
      await Promise.all(
        [
          "category-predictions",
          "catalog",
          "search",
          "recommendations",
          "audit-logs",
        ].map((key) => cache.invalidateQueries({ queryKey: [key] })),
      );
    },
  });
  const displayed = save.data ?? run;
  const editable = displayed.review_status === "PENDING";
  return (
    <article className="rounded-xl border bg-white p-5">
      <h2 className="text-lg font-semibold">{run.book_title}</h2>
      <p className="my-2 text-sm">
        {t.states[displayed.review_status]} ·{" "}
        {new Date(run.created_at).toLocaleString("kk-KZ")}
      </p>
      <p className="text-sm text-muted-foreground">
        {run.model_name} · {t.threshold}: {run.threshold.toFixed(3)}
      </p>
      {editable ? (
        <>
          <fieldset disabled={save.isPending} className="mt-4 space-y-4">
            {!run.predictions.length && <p>{t.noCandidates}</p>}
            {run.predictions.map((row) => (
              <label key={row.id} className="flex gap-3 items-start">
                <input
                  type="checkbox"
                  checked={selected.includes(row.category_id)}
                  onChange={(event) =>
                    setSelected(
                      event.target.checked
                        ? [...selected, row.category_id]
                        : selected.filter((id) => id !== row.category_id),
                    )
                  }
                />
                <span>
                  {row.name}{" "}
                  <span className="text-sm text-muted-foreground">
                    (
                    {row.score_kind === "COSINE_SIMILARITY"
                      ? t.similarity
                      : t.probability}
                    : {row.confidence.toFixed(3)})
                  </span>
                </span>
              </label>
            ))}
            <div className="flex flex-wrap gap-3">
              <Button
                variant="outline"
                onClick={() =>
                  setSelected(run.predictions.map((row) => row.category_id))
                }
              >
                {t.accept}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setSelected([]);
                  setManual([]);
                }}
              >
                {t.reject}
              </Button>
            </div>
            <p className="font-medium">{t.extra}</p>
            <ReferencePicker
              kind="categories"
              selected={manual}
              onChange={setManual}
            />
            <Button
              onClick={() => {
                if (window.confirm(t.confirm)) save.mutate();
              }}
            >
              {t.save}
            </Button>
          </fieldset>
          {save.isError && <Failure error={save.error} />}
        </>
      ) : (
        <>
          <p className="mt-4 font-medium">{t.final}</p>
          <p>
            {displayed.selected_categories.map((row) => row.name).join(", ") ||
              "—"}
          </p>
          <ul className="mt-3 text-sm">
            {displayed.predictions.map((row) => (
              <li key={row.id}>
                {row.name}:{" "}
                {row.accepted ? t.states.ACCEPTED : t.states.REJECTED}
              </li>
            ))}
          </ul>
        </>
      )}
      {save.isSuccess && (
        <p role="status" className="mt-3 text-primary">
          {t.success}
        </p>
      )}
    </article>
  );
}
