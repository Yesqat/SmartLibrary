import { BookEditor } from "@/features/catalog/book-editor";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <BookEditor root="/admin" id={id} />;
}
