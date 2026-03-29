"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

const ThreeHero = dynamic(() => import("./ThreeHero"), { ssr: false });

const S: Record<string, React.CSSProperties> = {
  section: {
    position: "relative", height: "100vh", display: "flex", alignItems: "center",
    justifyContent: "center", overflow: "hidden",
  },
  overlay: {
    position: "relative", zIndex: 1, textAlign: "center",
    maxWidth: 720, padding: "0 24px",
  },
  status: {
    fontSize: 11, fontWeight: 400, letterSpacing: "0.12em", color: "#3F3F46",
    marginBottom: 32, fontFamily: "inherit",
  },
  dot: { color: "#4ADE80" },
  h1: {
    fontSize: "clamp(36px, 5.5vw, 68px)", fontWeight: 700, lineHeight: 1.05,
    letterSpacing: "-0.03em", color: "#E4E4E7", margin: "0 0 24px",
    fontFamily: "inherit",
  },
  accent: { color: "#4ADE80" },
  sub: {
    fontSize: 14, fontWeight: 400, lineHeight: 1.75, color: "#71717A",
    maxWidth: 520, margin: "0 auto 32px", fontFamily: "inherit",
  },
  ctas: { display: "flex", gap: 16, justifyContent: "center", marginBottom: 40 },
  primary: {
    background: "#4ADE80", color: "#0C0C0E", border: "none", borderRadius: 0,
    padding: "10px 24px", fontSize: 13, fontWeight: 500, cursor: "pointer",
    fontFamily: "inherit", transition: "opacity 0.2s",
  },
  secondary: {
    background: "none", color: "#71717A", border: "none", borderRadius: 0,
    padding: "10px 24px", fontSize: 13, fontWeight: 400, cursor: "pointer",
    fontFamily: "inherit", transition: "color 0.2s",
  },
  thought: {
    background: "#16161A", border: "1px solid rgba(255,255,255,0.18)",
    borderRadius: 0, padding: 0, maxWidth: 520, margin: "0 auto",
    textAlign: "left", fontFamily: "inherit", overflow: "hidden",
  },
  thoughtHeader: {
    padding: "8px 14px", borderBottom: "1px solid rgba(255,255,255,0.18)",
    fontSize: 11, letterSpacing: "0.12em", color: "#3F3F46",
    display: "flex", justifyContent: "space-between",
  },
  thoughtBody: {
    padding: "12px 14px", fontSize: 12, lineHeight: 1.7, color: "#71717A",
    fontFamily: "inherit", margin: 0, whiteSpace: "pre-wrap",
  },
};

export default function Hero() {
  const overlayRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const el = overlayRef.current;
    if (!el) return;
    const children = Array.from(el.children) as HTMLElement[];
    children.forEach((child, i) => {
      child.style.opacity = "0";
      child.style.transform = "translateY(14px)";
      child.style.transition = `opacity 0.6s ease ${i * 0.1}s, transform 0.6s ease ${i * 0.1}s`;
    });
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        children.forEach((child) => {
          child.style.opacity = "1";
          child.style.transform = "translateY(0)";
        });
      });
    });
  }, []);

  return (
    <section style={S.section}>
      <ThreeHero />
      <div ref={overlayRef} style={S.overlay}>
        <div style={S.status}>
          <span style={S.dot}>■</span> LIVE&nbsp;&nbsp;·&nbsp;&nbsp;markets_active=847&nbsp;&nbsp;·&nbsp;&nbsp;agent_cycle=00:00:23&nbsp;&nbsp;·&nbsp;&nbsp;last_signal=+0.08
        </div>
        <h1 style={S.h1}>
          the market <span style={S.accent}>knows</span>.<br />
          we reason <span style={S.accent}>faster</span>.
        </h1>
        <p style={S.sub}>
          MarketMind watches Polymarket 24/7, cross-references breaking news, and surfaces high-confidence trades — with full reasoning shown.
        </p>
        <div style={S.ctas}>
          <button
            style={S.primary}
            onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.opacity = "0.85")}
            onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.opacity = "1")}
            onClick={() => router.push("/markets")}
          >{"> run_agent"}</button>
          <button
            style={S.secondary}
            onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.color = "#4ADE80")}
            onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.color = "#71717A")}
            onClick={() => router.push("/markets")}
          >{"_ view_markets →"}</button>
        </div>
        <div style={S.thought}>
          <div style={S.thoughtHeader}>
            <span>agent_thought</span>
            <span>4.2s ago</span>
          </div>
          <pre style={S.thoughtBody}>
{`Thought for 4.2s · confidence=`}<span style={{ color: "#4ADE80" }}>0.81</span>{`
"FED_CUTS_JUNE market at 0.31 — but 3 major news
 sources suggest 67% probability. Divergence=+36%"`}
          </pre>
        </div>
      </div>
    </section>
  );
}
