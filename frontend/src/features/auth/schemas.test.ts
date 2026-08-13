import { describe, expect, it } from "vitest";
import { changePasswordSchema, loginSchema } from "./schemas";

describe("loginSchema", () => {
  it("rejects an invalid email", () => {
    expect(loginSchema.safeParse({ email: "not-an-email", password: "x" }).success).toBe(false);
  });

  it("accepts a valid payload", () => {
    expect(loginSchema.safeParse({ email: "a@b.com", password: "secret" }).success).toBe(true);
  });
});

describe("changePasswordSchema", () => {
  it("rejects mismatched confirmation", () => {
    const result = changePasswordSchema.safeParse({
      currentPassword: "old-password",
      newPassword: "a-very-strong-password",
      confirmPassword: "different",
    });
    expect(result.success).toBe(false);
  });

  it("rejects a new password shorter than 12 characters", () => {
    const result = changePasswordSchema.safeParse({
      currentPassword: "old-password",
      newPassword: "short",
      confirmPassword: "short",
    });
    expect(result.success).toBe(false);
  });

  it("accepts a valid payload", () => {
    const result = changePasswordSchema.safeParse({
      currentPassword: "old-password",
      newPassword: "a-very-strong-password",
      confirmPassword: "a-very-strong-password",
    });
    expect(result.success).toBe(true);
  });
});
