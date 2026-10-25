import { redirect } from "next/navigation";

import AuthForm from "@/components/AuthForm";
import { isDemo } from "@/lib/demo";
import { getSession } from "@/lib/lang";

export default async function LoginPage() {
  const { t, account } = await getSession();
  if (account || isDemo()) redirect("/"); // already signed in, or no accounts in the public demo
  return (
    <div className="page">
      <header className="page-head">
        <h1>{t.account.title}</h1>
        <p className="lede">{t.account.lede}</p>
      </header>
      <AuthForm t={t} />
    </div>
  );
}
