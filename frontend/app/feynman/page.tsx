import FeynmanForm from "@/components/FeynmanForm";
import Icon from "@/components/Icon";
import { getNotions } from "@/lib/api";
import { getSession } from "@/lib/lang";

export default async function FeynmanPage({ searchParams }: { searchParams: Promise<{ notion?: string }> }) {
  const { lang, t, course } = await getSession();
  const { notion } = await searchParams;
  const notions = course ? await getNotions(lang, course.id) : [];
  return (
    <div className="page">
      <header className="page-head">
        <span className="eyebrow">{course?.title}</span>
        <h1>{t.feynman.title}</h1>
        <p className="lede">{t.feynman.lede}</p>
      </header>
      {course && notions.length > 0 ? (
        <FeynmanForm key={course.id} notions={notions} lang={lang} t={t} course={course.id} initialNotion={notion} />
      ) : (
        <p className="callout">
          <Icon name="info" />
          <span>
            {t.map.noNotions}
            <code className="code">uv run python -m course.add {course?.id ?? "<id>"}</code>
          </span>
        </p>
      )}
    </div>
  );
}
