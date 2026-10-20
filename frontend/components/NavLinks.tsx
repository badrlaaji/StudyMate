"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import Icon, { type IconName } from "@/components/Icon";
import type { Dict } from "@/lib/i18n";

const ITEMS: { href: string; key: keyof Dict["nav"]; icon: IconName }[] = [
  { href: "/", key: "map", icon: "progress" },
  { href: "/study", key: "study", icon: "ask" },
  { href: "/feynman", key: "feynman", icon: "feynman" },
  { href: "/quiz", key: "quiz", icon: "quiz" },
  { href: "/library", key: "library", icon: "library" },
];

// Main navigation: sidebar on desktop, bottom tab bar on small screens.
export default function NavLinks({ t, variant }: { t: Dict; variant: "nav" | "tabbar" }) {
  const pathname = usePathname();
  return (
    <nav className={variant} aria-label={t.nav.label}>
      {ITEMS.map((item) => (
        <Link key={item.href} href={item.href} aria-current={pathname === item.href ? "page" : undefined}>
          <Icon name={item.icon} />
          <span>{t.nav[item.key]}</span>
          {variant === "nav" && item.href === "/study" && (
            <span className="nav-hint">
              <kbd>/</kbd>
            </span>
          )}
        </Link>
      ))}
    </nav>
  );
}
