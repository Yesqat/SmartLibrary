import type { QueryClient } from "@tanstack/react-query";
import type { Reservation } from "./api";

const prefix = ["reservation-created-feedback"] as const;
const lifetime = 30_000;

export type CreationFeedback = {
  reservationId: string;
  bookId: string;
  userId: string;
  createdAt: number;
};

export function recordCreationFeedback(
  cache: QueryClient,
  userId: string,
  row: Reservation,
) {
  if (row.status !== "READY" && row.status !== "WAITING") return;
  cache.setQueryDefaults(prefix, { gcTime: lifetime });
  cache.setQueryData<CreationFeedback>([...prefix, userId, row.id], {
    reservationId: row.id,
    bookId: row.book_id,
    userId,
    createdAt: Date.now(),
  });
}

export function takeCreationFeedback(
  cache: QueryClient,
  userId: string,
  reservationId: string,
) {
  const queryKey = [...prefix, userId, reservationId];
  const marker = cache.getQueryData<CreationFeedback>(queryKey);
  if (marker) cache.removeQueries({ queryKey, exact: true });
  return marker;
}

export function matchesCreationFeedback(
  marker: CreationFeedback,
  userId: string,
  row: Reservation,
) {
  const age = Date.now() - marker.createdAt;
  return (
    marker.userId === userId &&
    marker.reservationId === row.id &&
    marker.bookId === row.book_id &&
    age >= 0 &&
    age < lifetime
  );
}
