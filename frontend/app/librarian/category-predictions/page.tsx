import { Suspense } from "react";
import { CategorizationPage } from "@/features/categorization/page";
export default function Page() {
  return (
    <Suspense>
      <CategorizationPage root="/librarian" />
    </Suspense>
  );
}
