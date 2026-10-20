"use client";

import { useRouter } from "next/navigation";

import { LANG_COOKIE, type Lang } from "@/lib/i18n";

// FR/EN button: store the choice in a cookie, then re-render the server pages.
export default function LangToggle({ lang, text, label }: { lang: Lang; text: string; label: string }) {
  const router = useRouter();
  const next: Lang = lang === "en" ? "fr" : "en";

  function switchLang() {
    document.cookie = `${LANG_COOKIE}=${next}; path=/; max-age=31536000; samesite=lax`;
    router.refresh();
  }

  return (
    <button type="button" className="secondary" onClick={switchLang} aria-label={label}>
      {text}
    </button>
  );
}
