import { Protected } from "@/features/auth/protected";
export default function AccountLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Protected>{children}</Protected>;
}
