import type { Metadata } from "next";
import "./globals.css";

import { NavShell } from "@/components/navigation/nav-shell";
import { ToastHost } from "@/components/ui/toast-host";
import { ReactQueryProvider } from "@/services/query/provider";

export const metadata: Metadata = {
  title: "LearnOS Frontend",
  description: "LearnOS frontend shell and state management",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <ReactQueryProvider>
          <NavShell>{children}</NavShell>
          <ToastHost />
        </ReactQueryProvider>
      </body>
    </html>
  );
}
