import type { User } from "@/services/api-client";

export function homeForRole(role: User["role"]) {
  return role === "ADMIN"
    ? "/admin"
    : role === "LIBRARIAN"
      ? "/librarian"
      : "/dashboard";
}
export function safeReturnTo(value: string | null, role: User["role"]) {
  // Explicit routes only; prevents open redirects and entering another role's area.
  if (value && /^\/books\/[0-9a-f-]{36}$/.test(value)) return value;
  if (
    role === "READER" &&
    value &&
    /^\/reservations(?:\/[0-9a-f-]{36})?$/.test(value)
  )
    return value;
  if (
    role === "READER" &&
    value &&
    ["/favorites", "/my-books", "/history", "/notifications"].includes(value)
  )
    return value;
  return value === "/account/security" ||
    value === "/account/profile" ||
    value === homeForRole(role)
    ? value
    : homeForRole(role);
}
