import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "react-hot-toast";

export const metadata: Metadata = {
  title: "TRACE-X | Cryptocurrency Fraud Investigation Platform",
  description:
    "TRACE-X — SIH26183: Real-time identification of fraud-linked cryptocurrency exchanges from victim-reported wallet addresses through automated blockchain analytics.",
  keywords: ["cryptocurrency", "fraud", "blockchain", "investigation", "VASP", "SIH26183"],
  authors: [{ name: "TRACE-X Team" }],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="bg-surface-900 text-surface-50 antialiased">
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#1e293b",
              color: "#f8fafc",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "10px",
              fontSize: "0.875rem",
            },
            success: { iconTheme: { primary: "#10b981", secondary: "#f8fafc" } },
            error: { iconTheme: { primary: "#ef4444", secondary: "#f8fafc" } },
          }}
        />
      </body>
    </html>
  );
}
