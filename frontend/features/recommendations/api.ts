import { apiMutation, apiRequest } from "@/services/api-client";
import type { components } from "@/types/api.generated";
export type RecommendationPage = components["schemas"]["RecommendationPage"];
export type RecommendationItem = components["schemas"]["RecommendationItem"];
export const recommendationApi = {
  list: (kind: "popular" | "similar" | "personalized", bookId?: string) =>
    apiRequest<RecommendationPage>(
      kind === "popular"
        ? "/books/popular"
        : kind === "similar"
          ? `/books/${bookId}/similar`
          : "/recommendations/me",
    ),
  impression: (receipt: string, bookId: string) =>
    apiMutation<components["schemas"]["ImpressionRead"]>(
      "/recommendations/impressions",
      "POST",
      { receipt, book_id: bookId },
    ),
  click: (id: string) =>
    apiMutation<void>(`/recommendations/impressions/${id}/click`, "POST"),
};
