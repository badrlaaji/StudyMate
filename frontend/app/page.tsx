import MasteryMap from "@/components/MasteryMap";
import { getMastery, getNotions, getPlan } from "@/lib/api";
import { getLang } from "@/lib/lang";

export default async function MapPage() {
  const { lang, t } = await getLang();
  const [notions, mastery, plan] = await Promise.all([getNotions(lang), getMastery(), getPlan(lang)]);
  return (
    <section>
      <h1>{t.map.title}</h1>
      <p className="muted">{t.map.intro}</p>
      <MasteryMap
        notions={notions}
        mastery={mastery.notions}
        plan={plan.plan}
        degraded={mastery.status === "degraded"}
        t={t}
      />
    </section>
  );
}
