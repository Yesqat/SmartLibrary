import { apiMutation, apiRequest, type User } from "@/services/api-client";
import type { components } from "@/types/api.generated";
import type { Book, Page } from "@/features/catalog/api";
export type Notification = components["schemas"]["NotificationRead"];
export type Loan = components["schemas"]["BorrowingView"];
export type Preferences = components["schemas"]["Preferences"];
export const readerApi = {
  summary: () =>
    apiRequest<components["schemas"]["ReaderSummary"]>("/reader/summary"),
  favorites: (page: number) =>
    apiRequest<Page<Book>>(`/favorites?page=${page}`),
  favorite: (id: string) =>
    apiRequest<components["schemas"]["FavoriteState"]>(`/favorites/${id}`),
  setFavorite: (id: string, enabled: boolean) =>
    apiMutation<void>(`/favorites/${id}`, enabled ? "POST" : "DELETE"),
  notifications: (page: number, unread: boolean) =>
    apiRequest<Page<Notification>>(
      `/notifications?page=${page}&unread=${unread}`,
    ),
  read: (id: string) =>
    apiMutation<Notification>(`/notifications/${id}/read`, "PATCH"),
  readAll: () => apiMutation<void>("/notifications/read-all", "POST"),
  loans: (page: number, history = false) =>
    apiRequest<Page<Loan>>(
      `/borrowings/me/${history ? "history" : "active"}?page=${page}`,
    ),
  profile: () => apiRequest<User>("/users/me"),
  saveProfile: (data: components["schemas"]["ProfileInput"]) =>
    apiMutation<User>("/users/me", "PATCH", data),
  preferences: () => apiRequest<Preferences>("/users/me/preferences"),
  savePreferences: (category_ids: string[]) =>
    apiMutation<Preferences>("/users/me/preferences", "PATCH", {
      category_ids,
    }),
  avatar: (file: File | null) => {
    if (!file) return apiMutation<User>("/users/me/avatar", "DELETE");
    const form = new FormData();
    form.set("file", file);
    return apiMutation<User>("/users/me/avatar", "POST", form);
  },
};
export const readerDate = (value: string) =>
  new Date(value).toLocaleString("kk-KZ");
export function notificationLink(row: Notification) {
  switch (row.related_entity_type) {
    case "RESERVATION":
      return `/reservations/${row.related_entity_id}`;
    case "BORROWING":
      return "/my-books";
    case "BOOK":
      return `/books/${row.related_entity_id}`;
  }
}
