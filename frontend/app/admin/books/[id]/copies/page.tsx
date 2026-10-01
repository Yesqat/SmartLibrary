import { CopyManager } from "@/features/catalog/copy-manager";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <CopyManager id={id} />;
}
