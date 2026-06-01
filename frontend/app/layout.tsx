import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "VBinvest",
  description: "VBinvest investing dashboard",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
