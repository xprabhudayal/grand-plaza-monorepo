import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hotel Voice AI Concierge - Grand Plaza Hotel",
  description: "Experience seamless room service ordering with our AI-powered voice concierge system",
  keywords: "hotel, room service, AI, voice assistant, concierge",
  authors: [{ name: "Grand Plaza Hotel" }],
  viewport: "width=device-width, initial-scale=1",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
