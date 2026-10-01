import { apiRequest, apiMutation } from "@/services/api-client";
import { queryString, type Page } from "@/features/catalog/api";
import type { Loan } from "@/features/reader/api";
import type { PickupPreview, ReaderOption } from "@/features/circulation/api";
import type { components } from "@/types/api.generated";
export type ReaderDetail = components["schemas"]["ReaderOperations"];
export type StaffReservation = components["schemas"]["StaffReservation"];
export const librarianApi = {
  dashboard: () =>
    apiRequest<components["schemas"]["LibrarianSummary"]>(
      "/librarian/dashboard",
    ),
  reader: (id: string) => apiRequest<ReaderDetail>(`/librarian/readers/${id}`),
  readers: (page: number, q: string, status: string) =>
    apiRequest<Page<ReaderOption>>(
      `/librarian/readers?${queryString({ page, q, ...(status ? { status } : {}) })}`,
    ),
  loans: (id: string, page: number, active: boolean) =>
    apiRequest<Page<Loan>>(
      `/librarian/readers/${id}/borrowings?${queryString({ page, active })}`,
    ),
  reservations: (page: number, q: string, status: string, reader_id?: string) =>
    apiRequest<Page<StaffReservation>>(
      `/librarian/reservations?${queryString({ page, q, ...(status ? { status } : {}), ...(reader_id ? { reader_id } : {}) })}`,
    ),
  overdue: (page: number, q: string, minimum_days: number, order: string) =>
    apiRequest<Page<Loan>>(
      `/librarian/borrowings/overdue?${queryString({ page, q, minimum_days, order })}`,
    ),
  manual: (reservation_number: string) =>
    apiMutation<PickupPreview>(
      "/librarian/reservations/verify-number",
      "POST",
      { reservation_number },
    ),
};
