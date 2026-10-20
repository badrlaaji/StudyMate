import type { Metadata } from "next";
import Link from "next/link";

import LangToggle from "@/components/LangToggle";
import { getLang } from "@/lib/lang";

import "./globals.css";

export const metadata: Metadata = {
  title: "StudyMate",
  description: "Study desk for Principles of Data Science (OpenStax), chapters 6-7.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const { lang, t } = await getLang();
  return (
    <html lang={lang}>
      <body>
        <header className="header">
          <Link href="/" className="brand">
            {t.app.name}
          </Link>
          <nav aria-label="main">
            <Link href="/">{t.nav.map}</Link>
            <Link href="/study">{t.nav.study}</Link>
            <Link href="/feynman">{t.nav.feynman}</Link>
            <Link href="/quiz">{t.nav.quiz}</Link>
          </nav>
          <LangToggle lang={lang} text={t.lang.switch} label={t.lang.label} />
        </header>
        <main>{children}</main>
        <footer className="footer">
          {t.footer.attribution}{" "}
          <a href="https://openstax.org/details/books/principles-data-science">{t.footer.book}</a>
        </footer>
      </body>
    </html>
  );
}
