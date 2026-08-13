import { describe, expect, it } from "vitest";
import { decodeAccessToken } from "./jwt";

function base64UrlEncode(obj: unknown): string {
  return btoa(JSON.stringify(obj)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

describe("decodeAccessToken", () => {
  it("decodes the payload segment of a JWT", () => {
    const payload = {
      sub: "user-1",
      role: "chef_equipe",
      perms: ["task:create"],
      exp: 1999999999,
    };
    const token = `header.${base64UrlEncode(payload)}.signature`;
    expect(decodeAccessToken(token)).toEqual(payload);
  });
});
