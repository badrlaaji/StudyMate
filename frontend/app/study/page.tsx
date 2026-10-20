import StudyDesk from "@/components/StudyDesk";
import { getLang } from "@/lib/lang";

export default async function StudyPage() {
  const { lang, t } = await getLang();
  return <StudyDesk lang={lang} t={t} />;
}
