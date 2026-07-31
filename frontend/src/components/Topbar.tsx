"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getMe, ManagerProfile } from "@/lib/api";
import { Logo } from "@/components/Logo";
import { initials } from "@/lib/colors";
import ThemeToggle from "@/components/ThemeToggle";

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/clients", label: "Clients" },
  { href: "/analysis", label: "Analysis" },
  { href: "/news", label: "News Feed" },
  { href: "/products", label: "Products" },
  { href: "/graph", label: "Product Fit" },
] as const;

export default function Topbar() {
  const pathname = usePathname();
  const [manager, setManager] = useState<ManagerProfile>({
    manager_name: "Ananya Rao",
    role: "Portfolio Manager",
    firm: "PwC India",
  });

  useEffect(() => {
    getMe()
      .then(setManager)
      .catch(() => {});
  }, []);

  return (
    <div className="topbar">
      <div className="topbar-inner">
        <Link href="/" className="brand">
          <Logo />
        </Link>
        <nav className="top-nav">
          {NAV_ITEMS.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} className={active ? "active" : ""}>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="topbar-right">
          <ThemeToggle />
          <div className="manager-profile" aria-label={`${manager.manager_name}, ${manager.role} at ${manager.firm}`}>
            <span className="manager-avatar">{initials(manager.manager_name)}</span>
            <span className="manager-profile-copy">
              <span className="manager-name">{manager.manager_name}</span>
              <span className="manager-role">{manager.role} · {manager.firm}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
