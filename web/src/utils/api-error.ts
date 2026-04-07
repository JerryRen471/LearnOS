import type { ApiError } from "@/types/api";

export function isApiError(value: unknown): value is ApiError {
  return Boolean(
    value &&
      typeof value === "object" &&
      "code" in value &&
      "status" in value &&
      "detail" in value &&
      typeof (value as ApiError).detail === "string",
  );
}

export function getErrorDetail(error: unknown): string {
  if (isApiError(error)) {
    return error.detail;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed";
}
