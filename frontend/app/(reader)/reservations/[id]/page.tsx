import { ReservationDetail } from "@/features/reservations/detail";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ReservationDetail id={id} />;
}
