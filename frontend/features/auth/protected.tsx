"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { kk } from "@/locales/kk";
import { refreshSession, type User } from "@/services/api-client";
import { useAuth } from "./auth-provider";
import { homeForRole } from "./navigation";

export function Protected({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles?: User["role"][];
}) {
  const auth = useAuth();
  const router = useRouter();
  const path = usePathname();
  useEffect(() => {
    if (auth.status === "anonymous")
      router.replace(`/login?next=${encodeURIComponent(path)}`);
  }, [auth.status, router, path]);
  if (auth.status === "error")
    return (
      <main className="mx-auto max-w-xl px-6 py-20">
        <p role="alert">{kk.auth.unavailable}</p>
        <Button
          className="mt-4"
          onClick={() => void refreshSession().catch(() => undefined)}
        >
          {kk.auth.retry}
        </Button>
      </main>
    );
  if (!auth.user || auth.status !== "authenticated")
    return (
      <main className="px-6 py-20" role="status">
        {kk.auth.loading}
      </main>
    );
  if (roles && !roles.includes(auth.user.role))
    return (
      <main className="mx-auto max-w-xl px-6 py-20">
        <h1 className="text-2xl font-semibold">{kk.auth.forbidden}</h1>
        <Link
          className="mt-6 inline-block underline"
          href={homeForRole(auth.user.role)}
        >
          {kk.auth.back}
        </Link>
      </main>
    );
  return children;
}
