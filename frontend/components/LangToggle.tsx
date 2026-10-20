"use client";

import { useRouter } from "next/navigation";

import { LANG_COOKIE, saveCookie, type Lang } from "@/lib/i18n";

const LANGS: { code: Lang; text: string; name: string }[] = [
  { code: "en", text: "EN", name: "English" },
  { code: "fr", text: "FR", name: "Français" },
];

// EN | FR segmented control: the choice goes to a cookie, the pages render again.
export default function LangToggle({ lang, label }: { lang: Lang; label: string }) {
  const router = useRouter();

  function choose(code: Lang) {
    saveCookie(LANG_COOKIE, code);
    router.refresh();
  }

  return (
    <div className="segmented" role="group" aria-label={label}>
      {LANGS.map((item) => (
        <button
          key={item.code}
          type="button"
          lang={item.code}
          title={item.name}
          aria-pressed={lang === item.code}
          onClick={() => choose(item.code)}
        >
          {item.text}
        </button>
      ))}
    </div>
  );
}
