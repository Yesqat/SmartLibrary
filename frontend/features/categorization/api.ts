import { apiMutation, apiRequest } from "@/services/api-client";
import type { components } from "@/types/api.generated";
import type { Page } from "@/features/catalog/api";
export type PredictionRun = components["schemas"]["PredictionRunRead"];
export const categorizationApi = {
  list: (page: number, bookId: string, status: string) => {
    const params = new URLSearchParams({ page_number: String(page) });
    if (bookId) params.set("book_id", bookId);
    if (status) params.set("status", status);
    return apiRequest<Page<PredictionRun>>(
      `/ai/category-predictions?${params}`,
    );
  },
  generate: (bookId: string, method: "classical" | "embedding") =>
    apiMutation<PredictionRun>("/ai/categorize", "POST", {
      book_id: bookId,
      method,
    }),
  review: (id: string, categories: string[]) =>
    apiMutation<PredictionRun>(
      `/ai/category-predictions/${id}/review`,
      "POST",
      { category_ids: categories },
    ),
};
