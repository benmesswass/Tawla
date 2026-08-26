import { describe, expect, it } from "vitest";
import { formatAmount, formatMoney } from "./currency";
import { getMarket } from "./market";

const TUNISIA = getMarket("tn");
const FRANCE = getMarket("fr");

describe("formatAmount", () => {
  it("uses three decimals and a period for Tunisia", () => {
    expect(formatAmount(22, TUNISIA)).toBe("22.000");
    expect(formatAmount(6.5, TUNISIA)).toBe("6.500");
  });

  it("uses two decimals and a comma for France", () => {
    expect(formatAmount(1234.5, FRANCE)).toBe("1234,50");
    expect(formatAmount(25, FRANCE)).toBe("25,00");
  });

  it("rounds to the market's decimals", () => {
    expect(formatAmount(22.0004, TUNISIA)).toBe("22.000");
    expect(formatAmount(22.0009, TUNISIA)).toBe("22.001");
  });
});

describe("formatMoney", () => {
  it("appends the market's own symbol after a non-breaking space", () => {
    expect(formatMoney(22, TUNISIA)).toBe("22.000 DT");
    expect(formatMoney(1234.5, FRANCE)).toBe("1234,50 €");
  });

  it("defaults to the current market", () => {
    expect(formatMoney(22)).toBe(formatMoney(22, TUNISIA));
  });
});
