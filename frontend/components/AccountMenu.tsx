"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import Icon from "@/components/Icon";
import { fmt, type Dict } from "@/lib/i18n";

// Signed in: who, and a sign-out button (the server clears the HttpOnly cookie). Else a link.
export default function AccountMenu({ email, t }: { email: string | null; t: Dict }) {
  const router = useRouter();

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.refresh();
  }

  if (!email) {
    return (
      <Link className="btn btn-sm btn-secondary account-link" href="/login">
        <Icon name="arrow" />
        {t.account.signIn}
      </Link>
    );
  }
  return (
    <div className="account">
      <span className="hint account-email">{fmt(t.account.signedInAs, { email })}</span>
      <button type="button" className="btn btn-sm btn-ghost" onClick={signOut}>
        {t.account.signOut}
      </button>
    </div>
  );
}
