import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stipple Art",
  description: "Convert images into stipple artwork",
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
