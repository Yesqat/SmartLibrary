"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Failure, Field, inputClass } from "@/features/catalog/shared";
import { circulation as t } from "@/locales/circulation";
import { circulationApi, type Inventory } from "./api";

export function InventorySearch({
  onFound,
}: {
  onFound: (value: Inventory | null) => void;
}) {
  const [number, setNumber] = useState("");
  const search = useMutation({
    mutationFn: circulationApi.inventory,
    onSuccess: onFound,
  });
  return (
    <form
      className="mb-8 max-w-xl space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        onFound(null);
        search.mutate(number.trim());
      }}
    >
      <Field label={t.inventory}>
        <input
          className={inputClass}
          value={number}
          onChange={(e) => {
            setNumber(e.target.value);
            onFound(null);
          }}
          required
          maxLength={100}
          disabled={search.isPending}
          autoComplete="off"
        />
      </Field>
      <Button disabled={search.isPending}>
        {search.isPending ? t.pending : t.findCopy}
      </Button>
      {search.isError && <Failure error={search.error} />}
    </form>
  );
}
