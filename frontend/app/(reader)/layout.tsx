import { Protected } from "@/features/auth/protected";
export default function ReaderLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Protected roles={["READER"]}>{children}</Protected>;
}
