import { Protected } from "@/features/auth/protected";
export default function LibrarianLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Protected roles={["LIBRARIAN"]}>{children}</Protected>;
}
