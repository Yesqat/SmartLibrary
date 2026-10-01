import { ReaderDetails } from "@/features/librarian/reader-detail";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ReaderDetails id={id} />;
}
