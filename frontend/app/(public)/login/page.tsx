import { AuthForm } from "@/features/auth/auth-form";
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ changed?: string }>;
}) {
  const query = await searchParams;
  return <AuthForm mode="login" passwordChanged={query.changed === "1"} />;
}
