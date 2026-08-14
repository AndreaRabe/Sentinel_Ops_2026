import { describe, expect, it } from "vitest";
import {
  formatDate,
  formatDateTime,
  fromDateTimeLocal,
  fullName,
  initials,
  toDateTimeLocal,
} from "./format";

describe("formatage des dates", () => {
  it("rend une date ISO au format francais", () => {
    expect(formatDateTime("2026-03-14T09:05:00Z")).toMatch(/^14\/03\/2026 \d{2}:\d{2}$/);
    expect(formatDate("2026-03-14T09:05:00Z")).toBe("14/03/2026");
  });

  it("affiche un tiret cadratin plutot que « Invalid Date »", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime(undefined)).toBe("—");
    expect(formatDateTime("pas-une-date")).toBe("—");
  });
});

describe("aller-retour avec <input type=datetime-local>", () => {
  it("reconstruit l'instant d'origine", () => {
    const iso = "2026-03-14T09:05:00.000Z";
    const roundTripped = fromDateTimeLocal(toDateTimeLocal(iso));
    expect(new Date(roundTripped!).getTime()).toBe(new Date(iso).getTime());
  });

  it("traite une saisie vide comme une absence de valeur", () => {
    expect(fromDateTimeLocal("")).toBeNull();
    expect(toDateTimeLocal(null)).toBe("");
  });

  it("ne renvoie jamais une date invalide", () => {
    expect(fromDateTimeLocal("n'importe quoi")).toBeNull();
  });
});

describe("identite", () => {
  it("compose les initiales en majuscules", () => {
    expect(initials("marie", "dupont")).toBe("MD");
  });

  it("compose le nom complet", () => {
    expect(fullName({ first_name: "Marie", last_name: "Dupont" })).toBe("Marie Dupont");
  });
});
