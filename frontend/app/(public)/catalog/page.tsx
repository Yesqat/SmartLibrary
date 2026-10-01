import { Suspense } from "react";
import { SearchCatalog } from "@/features/catalog/search-catalog";
import { catalog } from "@/locales/catalog";
export default function Page() {
  return (
    <Suspense fallback={<p role="status">{catalog.loading}</p>}>
      <SearchCatalog />
    </Suspense>
  );
}
