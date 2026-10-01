"use client";
import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  CatalogShell,
  Failure,
  Field,
  inputClass,
} from "@/features/catalog/shared";
import { catalog } from "@/locales/catalog";
import { circulation as t } from "@/locales/circulation";
import { circulationApi, type Inventory, type Condition } from "./api";
import { InventorySearch } from "./inventory-search";
import { reader as rt } from "@/locales/reader";
import { librarian as lt } from "@/locales/librarian";

function ReturnForm({ inventory }: { inventory: Inventory }) {
  const loan = inventory.active_borrowing;
  const [condition, setCondition] = useState<Condition>(
    inventory.physical_copy.condition,
  );
  const cache = useQueryClient();
  const close = useMutation({
    mutationFn: (lost: boolean) => {
      if (!loan) throw new Error("No active borrowing");
      return lost
        ? circulationApi.lost(loan.id)
        : circulationApi.returnBook(loan.id, condition);
    },
    onSuccess: async () => {
      await Promise.all(
        [
          "catalog",
          "recommendations",
          "search",
          "favorites",
          "reader-summary",
          "borrowings",
          "reservations",
          "notifications",
          "readers",
          "librarian-dashboard",
        ].map((key) => cache.invalidateQueries({ queryKey: [key] })),
      );
    },
  });
  const resulting = useQuery({
    queryKey: ["inventory-result", inventory.physical_copy.id, close.data?.id],
    queryFn: () =>
      circulationApi.inventory(inventory.physical_copy.inventory_number),
    enabled: close.isSuccess,
  });
  return (
    <section className="rounded-xl border bg-white p-6">
      <h2 className="text-xl font-semibold">{inventory.book_title}</h2>
      <p className="mt-2">
        {t.inventory}: {inventory.physical_copy.inventory_number}
      </p>
      {!loan ? (
        <p className="mt-5">{t.noLoan}</p>
      ) : (
        <>
          <p className="mt-4">
            {t.reader}: {loan.reader_name}
          </p>
          <p>
            {t.due}: {new Date(loan.due_at).toLocaleString("kk-KZ")}
          </p>
          <p>
            {rt.borrowed}: {new Date(loan.borrowed_at).toLocaleString("kk-KZ")}
          </p>
          <p>
            {lt.status}: {rt.states[loan.is_overdue ? "OVERDUE" : loan.status]}
          </p>
          <fieldset
            disabled={close.isPending || close.isSuccess}
            className="mt-6 max-w-xl space-y-4"
          >
            <Field label={t.condition}>
              <select
                className={inputClass}
                value={condition}
                onChange={(e) => setCondition(e.target.value as Condition)}
              >
                {Object.entries(catalog.conditions).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <div className="flex flex-wrap gap-4">
              <Button
                onClick={() => {
                  if (window.confirm(t.confirmReturn)) close.mutate(false);
                }}
              >
                {close.isPending ? t.pending : t.returnBook}
              </Button>
              <Button
                variant="outline"
                className="text-destructive"
                onClick={() => {
                  if (window.confirm(t.confirmLost)) close.mutate(true);
                }}
              >
                {t.lost}
              </Button>
            </div>
          </fieldset>
          {close.isError && <Failure error={close.error} />}
          {close.isSuccess && (
            <p role="status" className="mt-6 font-semibold">
              {close.data.status === "LOST" ? t.lostSuccess : t.returned}
            </p>
          )}
          {close.isSuccess &&
            (resulting.isPending ? (
              <p role="status">{t.pending}</p>
            ) : resulting.isError ? (
              <Failure
                error={resulting.error}
                retry={() => void resulting.refetch()}
              />
            ) : (
              <p className="mt-3">
                {lt.resultingCopy}:{" "}
                {catalog.statuses[resulting.data.physical_copy.status]}
              </p>
            ))}
        </>
      )}
    </section>
  );
}
export function ReturnBook() {
  const [inventory, setInventory] = useState<Inventory | null>(null);
  return (
    <CatalogShell title={t.returnTitle}>
      <InventorySearch onFound={setInventory} />
      {inventory && (
        <ReturnForm
          key={inventory.active_borrowing?.id ?? inventory.physical_copy.id}
          inventory={inventory}
        />
      )}
    </CatalogShell>
  );
}
