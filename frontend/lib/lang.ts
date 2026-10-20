// Server-side helper: read the interface language from the cookie.
import { cookies } from "next/headers";

import { DICTS, LANG_COOKIE, toLang, type Dict, type Lang } from "@/lib/i18n";

export async function getLang(): Promise<{ lang: Lang; t: Dict }> {
  const store = await cookies();
  const lang = toLang(store.get(LANG_COOKIE)?.value);
  return { lang, t: DICTS[lang] };
}
