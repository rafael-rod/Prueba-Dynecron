import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Chat con tus Documentos",
  description: "Sube documentos y haz preguntas sobre su contenido.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" data-theme="dark">
      <body className={`${inter.className}`}>
        <div className="min-h-screen app-gradient">
          <header className="sticky top-0 z-30 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-black/30 border-b border-[--color-border]">
            <div className="mx-auto max-w-6xl px-4 md:px-8 h-16 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="size-8 rounded-xl bg-[--color-primary]" />
                <span className="text-sm font-semibold tracking-wide">Dynecron Docs</span>
              </div>
              <nav className="hidden md:flex items-center gap-6 text-sm text-gray-400">
                <Link href="/" className="hover:text-[--color-foreground]">Inicio</Link>
                <Link href="/chat" className="hover:text-[--color-foreground]">Chats</Link>
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-4 md:px-8 py-8 md:py-12">
            {children}
          </main>
          <footer className="border-t border-[--color-border] py-6 text-center text-xs text-gray-500">
            <div className="mx-auto max-w-6xl px-4 md:px-8">
              Hecho con ❤️ por Rafael Rodriguez para chatear con tus documentos
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}