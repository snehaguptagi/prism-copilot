"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getMe } from "@/lib/api";
import { LogoMark } from "@/components/Logo";

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/clients", label: "Clients" },
  { href: "/analysis", label: "Analysis" },
  { href: "/news", label: "News Feed" },
  { href: "/products", label: "Products" },
] as const;

export default function Topbar() {
  const pathname = usePathname();
  const [managerName, setManagerName] = useState<string>("Portfolio Manager");

  useEffect(() => {
    getMe()
      .then((me) => setManagerName(me.manager_name))
      .catch(() => {});
  }, []);

  return (
    <div className="topbar">
      <div className="topbar-inner">
        <Link href="/" className="brand">
          <LogoMark size={26} />
          <span className="brand-word">PRISM</span>
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
        <div className="user-chip">{managerName}</div>
      </div>
    </div>
  );
}
