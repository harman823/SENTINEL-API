import type { Metadata } from "next";
import { Space_Mono, Rethink_Sans } from "next/font/google";
import "./globals.css";

const rethinkSans = Rethink_Sans({
  variable: "--font-rethink-sans",
  subsets: ["latin"],
});

const spaceMono = Space_Mono({
  variable: "--font-space-mono",
  subsets: ["latin"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "SENTINEL-API — AI-Powered API Testing",
  description:
    "Upload your OpenAPI spec and let our AI pipeline generate comprehensive tests, find vulnerabilities, and produce actionable reports.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${rethinkSans.variable} ${spaceMono.variable} antialiased`}
        style={{ fontFamily: "var(--font-rethink-sans), sans-serif" }}
      >
        {children}
      </body>
    </html>
  );
}
