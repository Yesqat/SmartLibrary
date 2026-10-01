import { describe, expect, it } from "vitest";
import { contentSecurityPolicy } from "@/lib/security-policy";

describe("CSP environment boundary", () => {
  it("requires a nonce and disallows evaluated or arbitrary inline production scripts", () => {
    const policy = contentSecurityPolicy("sample-nonce", false);
    const scripts = policy
      .split(";")
      .find((part) => part.trim().startsWith("script-src"))!;
    expect(scripts).toContain("'nonce-sample-nonce'");
    expect(scripts).toContain("'strict-dynamic'");
    expect(scripts).not.toMatch(/unsafe-inline|unsafe-eval/);
    expect(policy).toContain("frame-ancestors 'none'");
    expect(policy).toContain("object-src 'none'");
    expect(policy).not.toContain("ws:");
  });
  it("allows development debugging only in development", () => {
    expect(contentSecurityPolicy("dev-nonce", true)).toContain("'unsafe-eval'");
  });
});
