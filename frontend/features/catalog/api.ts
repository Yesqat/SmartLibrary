import { apiRequest, apiMutation } from "@/services/api-client";
import type { components } from "@/types/api.generated";
export type Book = components["schemas"]["BookRead"];
export type Copy = components["schemas"]["CopyRead"];
export type BookInput = components["schemas"]["BookCreate"];
export type CopyInput = components["schemas"]["CopyCreate"];
export type CopyPatch = components["schemas"]["CopyPatch"];
export type Reference =
  | components["schemas"]["AuthorRead"]
  | components["schemas"]["CategoryRead"]
  | components["schemas"]["PublisherRead"];
export type ReferenceKind = "authors" | "categories" | "publishers";
export type Page<T> = {
  items: T[];
  total: number;
  pages: number;
  page: number;
  page_size: number;
};
export const label = (row: Reference) =>
  "full_name" in row ? row.full_name : row.name;
export function queryString(values: Record<string, string | number | boolean>) {
  return new URLSearchParams(
    Object.entries(values).map(([key, value]) => [key, String(value)]),
  ).toString();
}
export const catalogApi = {
  books: (page: number, q: string, archived = false) =>
    apiRequest<Page<Book>>(
      `/books?${queryString({ page, q, include_archived: archived })}`,
    ),
  book: (id: string, archived = false) =>
    apiRequest<Book>(`/books/${id}?include_archived=${archived}`),
  save: (input: BookInput, id?: string) =>
    apiMutation<Book>(
      id ? `/books/${id}` : "/books",
      id ? "PATCH" : "POST",
      input,
    ),
  copies: (id: string, page: number, archived = true) =>
    apiRequest<Page<Copy>>(
      `/books/${id}/copies?${queryString({ page, include_archived: archived })}`,
    ),
  references: (kind: ReferenceKind, q = "", page = 1, archived = false) =>
    apiRequest<Page<Reference>>(
      `/${kind}?${queryString({ q, page, include_archived: archived })}`,
    ),
};

export const bookDetailQuery = (id: string) => ({
  queryKey: ["catalog", "book", id],
  queryFn: () => catalogApi.book(id),
});
