"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const S: Record<string, React.CSSProperties> = {
  nav: {
    position: "fixed", top: 0, left: 0, right: 0, height: 48, zIndex: 100,
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "0 24px", borderBottom: "1px solid rgba(255,255,255,0.18)",
    transition: "background 0.3s, backdrop-filter 0.3s",
    fontFamily: "'JetBrains Mono', monospace",
  },
  logo: { display: "flex", alignItems: "center", gap: 8 },
  mm: { color: "#4ADE80", fontSize: 13, fontWeight: 500 },
  name: { color: "#E4E4E7", fontSize: 13, fontWeight: 500 },
  links: { display: "flex", alignItems: "center", gap: 20 },
  link: {
    color: "#71717A", fontSize: 12, fontWeight: 400, background: "none",
    border: "none", cursor: "pointer", fontFamily: "inherit", padding: 0,
    transition: "color 0.2s", textDecoration: "none",
  },
  btn: {
    color: "#71717A", fontSize: 12, fontWeight: 400, background: "none",
    border: "1px solid rgba(255,255,255,0.18)", borderRadius: 0, padding: "6px 14px",
    cursor: "pointer", fontFamily: "inherit", transition: "border-color 0.2s, color 0.2s",
  },
};

const navLinks = [
  { label: "_markets", href: "/markets" },
  { label: "_agent", href: "/markets" },
  { label: "_dashboard", href: "/markets" },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", h, { passive: true });
    return () => window.removeEventListener("scroll", h);
  }, []);

  return (
    <nav style={{
      ...S.nav,
      background: scrolled ? "rgba(12,12,14,0.92)" : "transparent",
      backdropFilter: scrolled ? "blur(10px)" : "none",
      WebkitBackdropFilter: scrolled ? "blur(10px)" : "none",
    }}>
      <Link href="/" style={{ ...S.logo, textDecoration: "none" }}>
        <span style={S.mm}>[MM]</span>
        <span style={S.name}>MarketMind</span>
      </Link>
      <div style={S.links}>
        {navLinks.map(({ label, href }) => (
          <Link
            key={label}
            href={href}
            style={S.link}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#4ADE80")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#71717A")}
          >
            {label}
          </Link>
        ))}
        <button
          style={S.btn}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = "#4ADE80";
            (e.currentTarget as HTMLButtonElement).style.color = "#4ADE80";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.18)";
            (e.currentTarget as HTMLButtonElement).style.color = "#71717A";
          }}
        >{"> connect_wallet"}</button>
      </div>
    </nav>
  );
}
