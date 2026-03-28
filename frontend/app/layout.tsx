import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MarketMind",
  description: "MarketMind monorepo frontend",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <nav className="mx-auto flex max-w-5xl items-center gap-6 text-sm font-medium">
            <Link href="/" className="text-zinc-900 dark:text-zinc-100">
              MarketMind
            </Link>
            <Link
              href="/markets"
              className="text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
            >
              Markets
            </Link>
            <Link
              href="/"
              className="text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
            >
              Stack check
            </Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
