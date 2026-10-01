import { apiMutation, apiRequest } from "@/services/api-client";
import type { components } from "@/types/api.generated";
import type { Page } from "@/features/catalog/api";
export type Conversation = components["schemas"]["ConversationRead"];
export type Message = components["schemas"]["MessageRead"];
export const assistantApi = {
  list: (page: number) =>
    apiRequest<Page<Conversation>>(`/ai/conversations?page=${page}`),
  create: () => apiMutation<Conversation>("/ai/conversations", "POST", {}),
  detail: (id: string, page: number) =>
    apiRequest<components["schemas"]["ConversationDetail"]>(
      `/ai/conversations/${id}?page=${page}`,
    ),
  send: (id: string, content: string, request_id: string) =>
    apiMutation<Message>(`/ai/conversations/${id}/messages`, "POST", {
      content,
      request_id,
    }),
};
