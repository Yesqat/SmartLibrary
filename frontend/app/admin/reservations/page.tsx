import { Suspense } from "react";
import { AdminReservations } from "@/features/admin/monitoring";
export default function Page() {
  return (
    <Suspense fallback={<p role="status">Жүктелуде…</p>}>
      <AdminReservations />
    </Suspense>
  );
}
