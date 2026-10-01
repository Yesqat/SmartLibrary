import { apiMutation, apiRequest } from "@/services/api-client";
import type { components } from "@/types/api.generated";
export type PickupPreview = components["schemas"]["PickupPreview"];
export type Borrowing = components["schemas"]["BorrowingRead"];
export type Inventory = components["schemas"]["InventoryLookup"];
export type ReaderOption = components["schemas"]["ReaderOption"];
export type Condition = components["schemas"]["CopyCondition"];
export const circulationApi = {
  inventory: (number: string) =>
    apiRequest<Inventory>(
      `/librarian/borrowings/by-inventory/${encodeURIComponent(number)}`,
    ),
  readers: (q: string) =>
    apiRequest<components["schemas"]["Page_ReaderOption_"]>(
      `/librarian/readers?${new URLSearchParams({ q, page_size: "10" })}`,
    ),
  direct: (data: components["schemas"]["DirectIssueInput"]) =>
    apiMutation<Borrowing>("/librarian/borrowings", "POST", data),
  returnBook: (id: string, condition: Condition) =>
    apiMutation<Borrowing>(`/librarian/borrowings/${id}/return`, "POST", {
      condition,
    }),
  lost: (id: string) =>
    apiMutation<Borrowing>(`/librarian/borrowings/${id}/lost`, "POST"),
  verify: (token: string) =>
    apiMutation<PickupPreview>("/librarian/qr/verify", "POST", { token }),
  issueReserved: (id: string, verification_token: string) =>
    apiMutation<Borrowing>(`/librarian/reservations/${id}/issue`, "POST", {
      verification_token,
    }),
};
