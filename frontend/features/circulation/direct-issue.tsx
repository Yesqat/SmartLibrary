"use client";
import { useRef, useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { CatalogShell, Failure } from "@/features/catalog/shared";
import { circulation as t } from "@/locales/circulation";
import { circulationApi, type Inventory, type ReaderOption } from "./api";
import { InventorySearch } from "./inventory-search";
import { ReaderPicker } from "./reader-picker";
import { librarianApi } from "@/features/librarian/api";
import { ReaderEligibility } from "@/features/librarian/reader-detail";

function DirectIssueForm({ inventory }: { inventory: Inventory }) {
  const [reader, setReader] = useState<ReaderOption | null>(null);
  const requestKey = useRef<string | null>(null);
  const eligibility = useQuery({
    queryKey: ["readers", reader?.id],
    queryFn: () => librarianApi.reader(reader!.id),
    enabled: !!reader,
    refetchInterval: 30000,
  });
  const cache = useQueryClient();
  const issue = useMutation({
    mutationFn: circulationApi.direct,
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
          "readers",
          "librarian-dashboard",
        ].map((key) => cache.invalidateQueries({ queryKey: [key] })),
      );
    },
  });
  return (
    <section className="rounded-xl border bg-white p-6">
      <h2 className="text-xl font-semibold">{inventory.book_title}</h2>
      <p className="mt-2">
        {t.inventory}: {inventory.physical_copy.inventory_number}
      </p>
      {inventory.physical_copy.status !== "AVAILABLE" ||
      inventory.physical_copy.archived_at ? (
        <p className="mt-5" role="status">
          {t.unavailable}
        </p>
      ) : (
        <>
          <ReaderPicker
            value={reader}
            disabled={issue.isPending || issue.isSuccess}
            onChange={(value) => {
              setReader(value);
              requestKey.current = null;
              issue.reset();
            }}
          />
          {reader &&
            (eligibility.isPending ? (
              <p role="status">{t.pending}</p>
            ) : eligibility.isError ? (
              <Failure
                error={eligibility.error}
                retry={() => void eligibility.refetch()}
              />
            ) : (
              <ReaderEligibility data={eligibility.data} />
            ))}
          {issue.isError && <Failure error={issue.error} />}
          {issue.isSuccess && (
            <div role="status" className="my-5">
              <p>{issue.data.status === "BORROWED" ? t.issued : t.previous}</p>
              <p>
                {t.due}: {new Date(issue.data.due_at).toLocaleString("kk-KZ")}
              </p>
            </div>
          )}
          <Button
            disabled={
              !reader ||
              !eligibility.data?.can_borrow ||
              eligibility.isError ||
              issue.isPending ||
              issue.isSuccess
            }
            onClick={() => {
              if (!reader || !window.confirm(t.confirmation)) return;
              requestKey.current ??= crypto.randomUUID();
              issue.mutate({
                user_id: reader.id,
                book_copy_id: inventory.physical_copy.id,
                idempotency_key: requestKey.current,
              });
            }}
          >
            {issue.isPending ? t.pending : t.issue}
          </Button>
        </>
      )}
    </section>
  );
}
export function DirectIssue() {
  const [inventory, setInventory] = useState<Inventory | null>(null);
  return (
    <CatalogShell title={t.directTitle}>
      <InventorySearch onFound={setInventory} />
      {inventory && (
        <DirectIssueForm
          key={inventory.physical_copy.id}
          inventory={inventory}
        />
      )}
    </CatalogShell>
  );
}
