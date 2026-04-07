import { ZodType } from "zod";

import type { ApiError } from "@/types/api";

const DEFAULT_TIMEOUT = 15000;
const DEFAULT_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type RequestConfig = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  timeoutMs?: number;
};

const statusToCode: Record<number, ApiError["code"]> = {
  400: "BAD_REQUEST",
  404: "NOT_FOUND",
};

function buildUrl(path: string): string {
  const base = DEFAULT_BASE_URL.endsWith("/") ? DEFAULT_BASE_URL.slice(0, -1) : DEFAULT_BASE_URL;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalizedPath}`;
}

function toApiError(payload: {
  status: number;
  detail: string;
  requestId?: string;
  raw?: unknown;
}): ApiError {
  let code: ApiError["code"];
  if (payload.status === 0) {
    code = "NETWORK_ERROR";
  } else if (payload.status >= 500) {
    code = "SERVER_ERROR";
  } else {
    code = statusToCode[payload.status] ?? "UNKNOWN_ERROR";
  }
  return {
    code,
    status: payload.status,
    detail: payload.detail,
    message: payload.detail,
    requestId: payload.requestId,
    raw: payload.raw,
  };
}

function parseErrorDetail(raw: unknown, fallbackText: string): string {
  if (!raw || typeof raw !== "object") {
    return fallbackText;
  }
  const detail = (raw as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => (typeof item === "string" ? item : JSON.stringify(item))).join("; ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return fallbackText;
}

export async function request<T>(config: RequestConfig, schema?: ZodType<T>): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.timeoutMs ?? DEFAULT_TIMEOUT);
  const finalSignal = config.signal ?? controller.signal;

  try {
    const response = await fetch(buildUrl(config.path), {
      method: config.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        ...config.headers,
      },
      body: config.body ? JSON.stringify(config.body) : undefined,
      signal: finalSignal,
    });

    const requestId = response.headers.get("x-request-id") ?? undefined;
    const text = await response.text();
    const raw = text ? JSON.parse(text) : undefined;

    if (!response.ok) {
      throw toApiError({
        status: response.status,
        detail: parseErrorDetail(raw, response.statusText || "Request failed"),
        requestId,
        raw,
      });
    }

    if (!schema) {
      return raw as T;
    }

    const parsed = schema.safeParse(raw);
    if (!parsed.success) {
      const parseError: ApiError = {
        code: "SCHEMA_VALIDATION_ERROR",
        status: response.status,
        detail: parsed.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`).join("; "),
        message: "Schema validation failed",
        requestId,
        raw,
      };
      throw parseError;
    }
    return parsed.data;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw {
        code: "TIMEOUT",
        status: 0,
        detail: "Request timed out",
        message: "Request timed out",
      } satisfies ApiError;
    }
    if (isApiError(error)) {
      throw error;
    }
    throw {
      code: "NETWORK_ERROR",
      status: 0,
      detail: error instanceof Error ? error.message : "Network error",
      message: "Network error",
      raw: error,
    } satisfies ApiError;
  } finally {
    clearTimeout(timeout);
  }
}

function isApiError(value: unknown): value is ApiError {
  return Boolean(
    value &&
      typeof value === "object" &&
      "code" in value &&
      "status" in value &&
      "detail" in value,
  );
}

export { DEFAULT_BASE_URL, DEFAULT_TIMEOUT };
