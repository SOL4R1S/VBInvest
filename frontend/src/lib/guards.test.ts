import { describe, expect, it } from "vitest";

import {
  boolField,
  isRecord,
  nonEmptyStringField,
  numberField,
  numberValue,
  readDetail,
  stringField,
  stringOrNull,
  stringOrEmpty,
} from "./guards";

describe("isRecord", () => {
  it("returns true for plain objects", () => {
    expect(isRecord({})).toBe(true);
    expect(isRecord({ a: 1 })).toBe(true);
  });

  it("returns false for null, arrays, and primitives", () => {
    expect(isRecord(null)).toBe(false);
    expect(isRecord([])).toBe(false);
    expect(isRecord("str")).toBe(false);
    expect(isRecord(42)).toBe(false);
    expect(isRecord(undefined)).toBe(false);
  });
});

describe("stringField", () => {
  it("extracts string values", () => {
    expect(stringField({ name: "NVDA" }, "name")).toBe("NVDA");
  });

  it("returns null for non-string or missing keys", () => {
    expect(stringField({ name: 42 }, "name")).toBeNull();
    expect(stringField({}, "name")).toBeNull();
  });
});

describe("nonEmptyStringField", () => {
  it("returns non-empty strings", () => {
    expect(nonEmptyStringField({ v: "hello" }, "v")).toBe("hello");
  });

  it("returns null for empty or whitespace-only strings", () => {
    expect(nonEmptyStringField({ v: "" }, "v")).toBeNull();
    expect(nonEmptyStringField({ v: "   " }, "v")).toBeNull();
  });
});

describe("numberField", () => {
  it("extracts finite numbers", () => {
    expect(numberField({ v: 3.14 }, "v")).toBe(3.14);
    expect(numberField({ v: 0 }, "v")).toBe(0);
  });

  it("rejects NaN, Infinity, and non-numbers", () => {
    expect(numberField({ v: NaN }, "v")).toBeNull();
    expect(numberField({ v: Infinity }, "v")).toBeNull();
    expect(numberField({ v: "42" }, "v")).toBeNull();
  });
});

describe("boolField", () => {
  it("extracts booleans", () => {
    expect(boolField({ v: true }, "v")).toBe(true);
    expect(boolField({ v: false }, "v")).toBe(false);
  });

  it("returns null for non-booleans", () => {
    expect(boolField({ v: 1 }, "v")).toBeNull();
    expect(boolField({ v: "true" }, "v")).toBeNull();
  });
});

describe("stringOrEmpty", () => {
  it("returns the string or empty", () => {
    expect(stringOrEmpty("hi")).toBe("hi");
    expect(stringOrEmpty(42)).toBe("");
    expect(stringOrEmpty(null)).toBe("");
  });
});

describe("numberValue", () => {
  it("returns finite numbers or 0", () => {
    expect(numberValue(99)).toBe(99);
    expect(numberValue(NaN)).toBe(0);
    expect(numberValue("x")).toBe(0);
  });
});

describe("stringOrNull", () => {
  it("returns non-empty strings or null", () => {
    expect(stringOrNull("ok")).toBe("ok");
    expect(stringOrNull("")).toBeNull();
    expect(stringOrNull(42)).toBeNull();
  });
});

describe("readDetail", () => {
  it("extracts detail from a record", () => {
    expect(readDetail({ detail: "not found" })).toBe("not found");
  });

  it("returns empty string for invalid payloads", () => {
    expect(readDetail(null)).toBe("");
    expect(readDetail({ detail: 42 })).toBe("");
    expect(readDetail("str")).toBe("");
  });
});
