import type { Metadata } from "next";
import localFont from "next/font/local";
import Link from "next/link";

import AccountMenu from "@/components/AccountMenu";
import BrandMark from "@/components/BrandMark";
import CourseSwitcher from "@/components/CourseSwitcher";
import Icon from "@/components/Icon";
import LangToggle from "@/components/LangToggle";
import NavLinks from "@/components/NavLinks";
import { isDemo } from "@/lib/demo";
import { getSession } from "@/lib/lang";

import "./globals.css";

// Local fonts only (SIL Open Font License, files in app/fonts).
const sans = localFont({
  src: "./fonts/bricolage-grotesque-latin.woff2",
  variable: "--font-sans",
  weight: "200 800",
  display: "swap",
});
const serif = localFont({
  src: "./fonts/literata-latin.woff2",
  variable: "--font-serif",
  weight: "200 900",
  display: "swap",
});

export const metadata: Metadata = {
  title: "StudyMate",
  description: "Study assistant for open textbooks: verified page citations, Feynman mode, quizzes and a mastery map.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const { lang, t, courses, course, account } = await getSession();
  const accounts = !isDemo(); // the public demo has no accounts
  return (
    <html lang={lang} className={`${sans.variable} ${serif.variable}`}>
      <body>
        <a className="skip-link" href="#content">
          {t.app.skip}
        </a>
        <div className="shell">
          <aside className="sidebar">
            <Link href="/" className="brand">
              <BrandMark />
              <span className="brand-name">
                {t.app.name}
                <span className="brand-tag">{t.app.tagline}</span>
              </span>
            </Link>
            <CourseSwitcher courses={courses} current={course} t={t} id="course-desktop" />
            <NavLinks t={t} variant="nav" />
            <div className="sidebar-foot">
              {accounts && <AccountMenu email={account?.email ?? null} t={t} />}
              <LangToggle lang={lang} label={t.lang.label} />
              {course && (
                <p>
                  {t.footer.content}
                  {lang === "fr" ? " : " : ": "}
                  <a href={course.book_url}>{course.title}</a>, {course.attribution}, {course.license}.
                </p>
              )}
              <p>{t.footer.license}</p>
            </div>
          </aside>

          <header className="topbar">
            <Link href="/" className="brand" aria-label={t.app.name}>
              <BrandMark />
            </Link>
            <CourseSwitcher courses={courses} current={course} t={t} id="course-mobile" />
            {accounts && !account && <AccountMenu email={null} t={t} />}
            <LangToggle lang={lang} label={t.lang.label} />
          </header>

          <main id="content" className="main">
            {isDemo() && (
              <p className="callout demo-banner" role="note">
                <Icon name="info" />
                <span>
                  {t.demo.banner}{" "}
                  <a href="https://github.com/badrlaaji/StudyMate">{t.demo.repo}</a>
                </span>
              </p>
            )}
            {children}
          </main>
          <NavLinks t={t} variant="tabbar" />
        </div>
      </body>
    </html>
  );
}
