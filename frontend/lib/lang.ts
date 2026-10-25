// Server-side helpers: interface language and current course, from the cookies.
import { cookies } from "next/headers";

import { accountFromToken, SESSION_COOKIE, type Account } from "@/lib/account";
import { getCourses, type Course } from "@/lib/api";
import { COURSE_COOKIE, DICTS, LANG_COOKIE, toLang, type Dict, type Lang } from "@/lib/i18n";

export async function getLang(): Promise<{ lang: Lang; t: Dict }> {
  const store = await cookies();
  const lang = toLang(store.get(LANG_COOKIE)?.value);
  return { lang, t: DICTS[lang] };
}

// The course in the cookie if it still exists, else the default one.
export async function getSession(): Promise<{
  lang: Lang;
  t: Dict;
  courses: Course[];
  course: Course | null;
  account: Account | null;
}> {
  const { lang, t } = await getLang();
  const courses = await getCourses(lang);
  const store = await cookies();
  const wanted = store.get(COURSE_COOKIE)?.value;
  const course = courses.find((c) => c.id === wanted) ?? courses.find((c) => c.default) ?? null;
  const account = accountFromToken(store.get(SESSION_COOKIE)?.value);
  return { lang, t, courses, course, account };
}
