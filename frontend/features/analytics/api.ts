import { apiRequest } from "@/services/api-client";
import type { components } from "@/types/api.generated";
export type Dates = { date_from?: string; date_to?: string };
export type Overview = components["schemas"]["OverviewAnalytics"];
export type Circulation = components["schemas"]["CirculationAnalytics"];
export type Inventory = components["schemas"]["InventoryAnalytics"];
export type Readers = components["schemas"]["ReaderAnalytics"];
export type Search = components["schemas"]["SearchAnalytics"];
export type AI = components["schemas"]["AIAnalytics"];
export type Point = components["schemas"]["CountPoint"];
export type Period = components["schemas"]["PeriodRead"];
function get<T>(section: string, dates: Dates) {
  const params = new URLSearchParams();
  if (dates.date_from) params.set("date_from", dates.date_from);
  if (dates.date_to) params.set("date_to", dates.date_to);
  return apiRequest<T>(`/admin/analytics/${section}?${params}`);
}
export const analyticsApi = {
  overview: (dates: Dates) => get<Overview>("overview", dates),
  circulation: (dates: Dates) => get<Circulation>("circulation", dates),
  inventory: (dates: Dates) => get<Inventory>("inventory", dates),
  readers: (dates: Dates) => get<Readers>("readers", dates),
  search: (dates: Dates) => get<Search>("search", dates),
  ai: (dates: Dates) => get<AI>("ai", dates),
};
