"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";
import { Failure } from "@/features/catalog/shared";
import { reservations as t } from "@/locales/reservations";
import { reservationApi } from "./api";

export function ReserveButton({
  bookId,
  available,
}: {
  bookId: string;
  available: number;
}) {
  const { user, status } = useAuth();
  const router = useRouter();
  const cache = useQueryClient();
  const action = useMutation({
    mutationFn: () => reservationApi.create(bookId),
    onSuccess: async (row) => {
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["catalog"] }),
        cache.invalidateQueries({ queryKey: ["recommendations"] }),
        cache.invalidateQueries({ queryKey: ["search"] }),
        cache.invalidateQueries({ queryKey: ["reservations"] }),
        cache.invalidateQueries({ queryKey: ["reader-summary"] }),
        cache.invalidateQueries({ queryKey: ["notifications"] }),
        cache.invalidateQueries({ queryKey: ["favorites"] }),
      ]);
      router.push(`/reservations/${row.id}`);
    },
  });
  if (status === "loading") return <p role="status">{t.loading}</p>;
  if (!user)
    return (
      <Button asChild>
        <Link href={`/login?next=${encodeURIComponent(`/books/${bookId}`)}`}>
          {t.login}
        </Link>
      </Button>
    );
  if (user.role !== "READER") return null;
  return (
    <div className="mt-4 space-y-3">
      <Button
        disabled={action.isPending || action.isSuccess}
        onClick={() => action.mutate()}
      >
        {action.isPending ? t.loading : available > 0 ? t.reserve : t.wait}
      </Button>
      <Link
        className="ml-4 text-sm text-primary underline"
        href="/reservations"
      >
        {t.title}
      </Link>
      {action.isError && <Failure error={action.error} />}
    </div>
  );
}
