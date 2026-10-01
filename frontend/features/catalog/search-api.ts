import { apiRequest, apiMutation } from "@/services/api-client";
import type { components } from "@/types/api.generated";
export type SearchPage = components["schemas"]["SearchPage"];
export type Autocomplete = components["schemas"]["Autocomplete"];
export type SearchSort = components["schemas"]["SearchSort"];
export const searchApi = {
  search: (params: URLSearchParams) =>
    apiRequest<SearchPage>(`/search?${params}`),
  autocomplete: (q: string, signal?: AbortSignal) =>
    apiRequest<Autocomplete>(
      `/search/autocomplete?${new URLSearchParams({ q })}`,
      { signal },
    ),
  click: (searchId: string, bookId: string) =>
    apiMutation<void>(`/search/${searchId}/click`, "POST", {
      book_id: bookId,
      event_id: crypto.randomUUID(),
    }),
};
