import { apiRequest, apiMutation } from "@/services/api-client";
import type { components } from "@/types/api.generated";
export type Reservation = components["schemas"]["ReservationRead"];
export type Credential = components["schemas"]["ReservationCredential"];
export const reservationApi = {
  create: (book_id: string) =>
    apiMutation<Reservation>("/reservations", "POST", { book_id }),
  list: (page: number, status: string, active?: boolean) =>
    apiRequest<components["schemas"]["Page_ReservationRead_"]>(
      `/reservations/me?page=${page}${status ? `&status=${status}` : ""}${active === undefined ? "" : `&active=${active}`}`,
    ),
  detail: (id: string) => apiRequest<Reservation>(`/reservations/${id}`),
  cancel: (id: string) =>
    apiMutation<Reservation>(`/reservations/${id}/cancel`, "POST"),
  qr: (id: string) => apiRequest<Credential>(`/reservations/${id}/qr`),
};
