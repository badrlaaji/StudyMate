// Two dictionaries, no i18n library: the language comes from the "lang" cookie.
import en from "@/i18n/en.json";
import fr from "@/i18n/fr.json";

export type Lang = "en" | "fr";
export type Dict = typeof en;

export const DICTS: Record<Lang, Dict> = { en, fr };
export const LANG_COOKIE = "lang";

export function toLang(value: string | undefined): Lang {
  return value === "fr" ? "fr" : "en";
}
