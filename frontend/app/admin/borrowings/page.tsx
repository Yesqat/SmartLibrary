import { Suspense } from "react";
import { AdminBorrowings } from "@/features/admin/monitoring";
export default function Page() {
  return (
    <Suspense fallback={<p role="status">Жүктелуде…</p>}>
      <AdminBorrowings />
    </Suspense>
  );
}
