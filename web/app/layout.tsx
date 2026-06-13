import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecondBrain",
  description: "Ask your company brain.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
