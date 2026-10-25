"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import Icon from "@/components/Icon";
import type { Dict } from "@/lib/i18n";

type Mode = "login" | "register";

async function post(path: string, body: object): Promise<number> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return response.status;
}

// Sign in, or create an account then sign in. The token never reaches this script.
export default function AuthForm({ t }: { t: Dict }) {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function message(status: number): string {
    if (status === 401) return t.account.wrong;
    if (status === 409) return t.account.taken;
    if (status === 400 || status === 422) return t.account.invalid;
    return t.account.down;
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = { email, password };
      if (mode === "register") {
        const created = await post("/api/auth/register", body);
        if (created !== 201) return setError(message(created));
      }
      const status = await post("/api/auth/login", body);
      if (status !== 200) return setError(message(status));
      router.push("/");
      router.refresh();
    } catch {
      setError(t.account.down);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="card stack auth-form" aria-labelledby="auth-title">
      <h2 id="auth-title">{mode === "login" ? t.account.login : t.account.register}</h2>
      <div className="field">
        <label className="field-label" htmlFor="email">
          {t.account.email}
        </label>
        <input id="email" className="input" type="email" autoComplete="email" required maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} />
      </div>
      <div className="field">
        <label className="field-label" htmlFor="password">
          {t.account.password}
        </label>
        <input
          id="password"
          className="input"
          type="password"
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          required
          minLength={8}
          maxLength={72}
          aria-describedby="password-hint"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <span id="password-hint" className="hint">
          {t.account.passwordHint}
        </span>
      </div>
      <div aria-live="polite">
        {error && (
          <p className="callout callout-warn" role="alert">
            <Icon name="alert" />
            {error}
          </p>
        )}
      </div>
      <button type="submit" className="btn btn-primary" disabled={busy} style={{ justifySelf: "start" }}>
        {busy ? t.account.working : mode === "login" ? t.account.submitLogin : t.account.submitRegister}
      </button>
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        style={{ justifySelf: "start" }}
        onClick={() => {
          setMode(mode === "login" ? "register" : "login");
          setError("");
        }}
      >
        {mode === "login" ? t.account.switchToRegister : t.account.switchToLogin}
      </button>
    </form>
  );
}
