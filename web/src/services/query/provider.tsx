"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useState } from "react";

import { getErrorDetail, isApiError } from "@/utils/api-error";
import { showToast } from "@/utils/toast-store";

export function ReactQueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({
          onError: (error) => {
            const detail = getErrorDetail(error);
            const status = isApiError(error) ? error.status : 0;
            const title =
              status === 404 ? "Not found" : status >= 500 ? "Server error" : "Request failed";
            showToast({ title, detail, variant: status >= 500 ? "warn" : "danger" });
          },
        }),
        mutationCache: new MutationCache({
          onError: (error) => {
            const detail = getErrorDetail(error);
            const status = isApiError(error) ? error.status : 0;
            const title =
              status === 404 ? "Not found" : status >= 500 ? "Server error" : "Request failed";
            showToast({ title, detail, variant: status >= 500 ? "warn" : "danger" });
          },
        }),
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            gcTime: 5 * 60_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
          mutations: {
            retry: 0,
          },
        },
      }),
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
