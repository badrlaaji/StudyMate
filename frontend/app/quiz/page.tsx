import { getLang } from "@/lib/lang";

// The quiz page arrives with the Spring service (step 9).
export default async function QuizPage() {
  const { t } = await getLang();
  return <h1>{t.nav.quiz}</h1>;
}
