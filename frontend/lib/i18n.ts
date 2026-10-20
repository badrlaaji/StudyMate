// Two dictionaries, no i18n library: the language comes from the "lang" cookie.
import en from "@/i18n/en.json";
import fr from "@/i18n/fr.json";

export type Lang = "en" | "fr";
export type Dict = typeof en;

export const DICTS: Record<Lang, Dict> = { en, fr };
export const LANG_COOKIE = "lang";
export const COURSE_COOKIE = "course";
const ONE_YEAR_S = 31536000;

export function toLang(value: string | undefined): Lang {
  return value === "fr" ? "fr" : "en";
}

// French typography puts a space before ":".
export function colon(lang: Lang): string {
  return lang === "fr" ? " : " : ": ";
}

// Fill "{name}" placeholders: fmt("Page {page}", { page: 3 }) -> "Page 3".
export function fmt(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => String(values[key] ?? match));
}

// Browser only: remember a choice (language or course) for the server pages.
export function saveCookie(name: string, value: string): void {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${ONE_YEAR_S}; samesite=lax`;
}

// PDF of a course, at a page (the browser PDF viewer reads #page=N).
export function pdfUrl(course: string, page?: number): string {
  const url = `/api/book.pdf?course=${encodeURIComponent(course)}`;
  return page ? `${url}#page=${page}` : url;
}
