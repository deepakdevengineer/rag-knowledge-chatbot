import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata = {
  title: "AI Assistant",
  description: "RAG-powered AI assistant — chat with your documents.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} antialiased`} style={{ height: "100vh", overflow: "hidden" }}>
        {children}
      </body>
    </html>
  );
}
