import PresencePanel from "@/components/PresencePanel";
import StudyDesk from "@/components/StudyDesk";
import { getNotions } from "@/lib/api";
import { demoPrompts, isDemo } from "@/lib/demo";
import { getSession } from "@/lib/lang";

export default async function StudyPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const { lang, t, course, account } = await getSession();
  if (!course) return <p className="callout callout-warn">{t.study.error}</p>;
  const page = Number((await searchParams).page);
  const notions = await getNotions(lang, course.id);
  return (
    <div className="page page-wide">
      <PresencePanel t={t} course={course.id} canSave={account !== null || isDemo()} />
      <StudyDesk
        // A new course starts a new conversation.
        key={course.id}
        lang={lang}
        t={t}
        course={course.id}
        scope={course.scope}
        examples={[...new Set([notions[0], notions[Math.floor(notions.length / 2)]])]
          .filter(Boolean)
          .map((notion) => notion.name)}
        initialPage={Number.isInteger(page) && page > 0 ? page : undefined}
        prompts={isDemo() ? demoPrompts(course.id, lang) : undefined}
        onlinePdf={isDemo() ? course.pdf_url : undefined}
      />
    </div>
  );
}
