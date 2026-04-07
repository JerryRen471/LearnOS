import { describe, expect, it } from "vitest";

import { getErrorDetail, isApiError } from "@/utils/api-error";

describe("api-error", () => {
  it("detects ApiError shape", () => {
    expect(isApiError({ code: "BAD_REQUEST", status: 400, detail: "x", message: "x" })).toBe(true);
    expect(isApiError(new Error("e"))).toBe(false);
  });

  it("extracts detail from ApiError", () => {
    expect(getErrorDetail({ code: "NOT_FOUND", status: 404, detail: "missing", message: "missing" })).toBe(
      "missing",
    );
  });

  it("falls back for Error", () => {
    expect(getErrorDetail(new Error("boom"))).toBe("boom");
  });
});
