import { apiMutation, apiRequest, type User } from "@/services/api-client";
import { queryString, type Page } from "@/features/catalog/api";
import type { components } from "@/types/api.generated";
export type Setting = components["schemas"]["SettingRead"];
export type AdminMetrics = components["schemas"]["AdminSummary"];
export const adminApi = {
  users: (params: URLSearchParams, librarians = false) =>
    apiRequest<Page<User>>(
      `/admin/${librarians ? "librarians" : "users"}?${params}`,
    ),
  user: (id: string) => apiRequest<User>(`/admin/users/${id}`),
  role: (id: string, role: User["role"]) =>
    apiMutation<User>(`/admin/users/${id}/role`, "PATCH", { role }),
  status: (id: string, status: User["status"]) =>
    apiMutation<User>(`/admin/users/${id}/status`, "PATCH", { status }),
  settings: () => apiRequest<Setting[]>("/admin/settings"),
  saveSettings: (changes: components["schemas"]["SettingChange"][]) =>
    apiMutation<Setting[]>("/admin/settings", "PATCH", { changes }),
  dashboard: () => apiRequest<AdminMetrics>("/admin/dashboard"),
  audit: (page: number, filters: Record<string, string>) =>
    apiRequest<components["schemas"]["Page_AuditRead_"]>(
      `/admin/audit-logs?${queryString({ page, ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)) })}`,
    ),
  inventory: (params: URLSearchParams) =>
    apiRequest<components["schemas"]["Page_InventoryRow_"]>(
      `/admin/inventory?${params}`,
    ),
  borrowings: (params: URLSearchParams) =>
    apiRequest<components["schemas"]["Page_BorrowingView_"]>(
      `/admin/borrowings?${params}`,
    ),
  reservations: (params: URLSearchParams) =>
    apiRequest<components["schemas"]["Page_StaffReservation_"]>(
      `/admin/reservations?${params}`,
    ),
};
