import FeynmanForm from "@/components/FeynmanForm";
import { getNotions } from "@/lib/api";
import { getLang } from "@/lib/lang";

export default async function FeynmanPage({
  searchParams,
}: {
  searchParams: Promise<{ notion?: string }>;
}) {
  const { lang, t } = await getLang();
  const { notion } = await searchParams;
  const notions = await getNotions(lang);
  return (
    <section>
      <h1>{t.feynman.title}</h1>
      <p className="muted">{t.feynman.intro}</p>
      <FeynmanForm notions={notions} lang={lang} t={t} initialNotion={notion} />
    </section>
  );
}
