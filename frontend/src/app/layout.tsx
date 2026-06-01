import type { Metadata } from "next";
import "../../app/globals.css";

export const metadata: Metadata = {
  title: "VBinvest",
  description: "DB-backed investing dashboard",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
