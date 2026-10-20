import QuizRunner from "@/components/QuizRunner";
import { getLang } from "@/lib/lang";

export default async function QuizPage() {
  const { lang, t } = await getLang();
  return (
    <section>
      <h1>{t.quiz.title}</h1>
      <p className="muted">{t.quiz.intro}</p>
      <QuizRunner lang={lang} t={t} />
    </section>
  );
}
