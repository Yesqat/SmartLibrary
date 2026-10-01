import { apiDownload } from "@/services/api-client";
import type { components } from "@/types/api.generated";
export type ReportInput = components["schemas"]["ReportInput"];
export const reportsApi = {
  generate: (data: ReportInput) => apiDownload("/admin/reports", data),
};
