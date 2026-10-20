import Link from "next/link";

import { getNotions } from "@/lib/api";
import { getLang } from "@/lib/lang";

// Mastery colours arrive with the Spring service (step 9).
export default async function MapPage() {
  const { lang, t } = await getLang();
  const notions = await getNotions(lang);
  return (
    <section>
      <h1>{t.nav.map}</h1>
      <p className="muted">{t.app.tagline}</p>
      <ul style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "0.75rem", padding: 0, listStyle: "none" }}>
        {notions.map((notion) => (
          <li key={notion.id} className="card">
            <strong>{notion.name}</strong>
            <p className="muted">{notion.section}</p>
            <Link href={`/feynman?notion=${notion.id}`}>{t.nav.feynman}</Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
