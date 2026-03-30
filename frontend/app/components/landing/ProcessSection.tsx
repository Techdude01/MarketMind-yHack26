"use client";

import { useEffect, useRef, useState } from "react";

const BORDER         = "rgba(255,255,255,0.18)";
const BORDER_BRIGHT  = "rgba(255,255,255,0.32)";
const BORDER_SECTION = "rgba(255,255,255,0.22)";

const steps = [
  {
    label: "[OBSERVE]", step: "01",
    desc: "Ingest live odds from Polymarket + real-time news feeds. 847 markets tracked simultaneously across all categories.",
    stats: [
      { key: "markets_scanned", value: "847",   color: "#E4E4E7" },
      { key: "sources_pulled",  value: "12",    color: "#E4E4E7" },
      { key: "snapshot_age",    value: "< 30s", color: "#4ADE80" },
    ],
  },
  {
    label: "[REASON]", step: "02",
    desc: "Cross-reference market prices against news sentiment, historical patterns, and expert consensus to surface hidden divergences.",
    stats: [
      { key: "divergence_score",  value: "+0.36", color: "#4ADE80" },
      { key: "thought_duration",  value: "2.3s",  color: "#E4E4E7" },
    ],
  },
  {
    label: "[ACT]", step: "03",
    desc: "Surface high-confidence trade signals with full reasoning chain attached. Every decision is completely auditable.",
    stats: [
      { key: "confidence",      value: "0.79",   color: "#4ADE80" },
      { key: "expected_value",  value: "+$0.22", color: "#4ADE80" },
      { key: "breakeven_prob",  value: "0.61",   color: "#E4E4E7" },
    ],
  },
];

type Step = typeof steps[0];

function NotebookCell({ s }: { s: Step }) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      data-anim
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: "#16161A",
        border: `1px solid ${hovered ? BORDER_BRIGHT : BORDER}`,
        borderLeft: `2px solid ${hovered ? "#4ADE80" : "transparent"}`,
        borderRadius: 0,
        marginBottom: 2,
        overflow: "hidden",
        transition: "border-color 0.2s, border-left-color 0.2s",
        fontFamily: "'JetBrains Mono', monospace",
        opacity: 0,
        transform: "translateY(16px)",
      }}
    >
      {/* Header row */}
      <div style={{
        display: "flex", justifyContent: "space-between", padding: "8px 14px",
        borderBottom: `1px solid ${BORDER}`,
        fontSize: 11, letterSpacing: "0.12em", color: "#3F3F46",
      }}>
        <span>{s.label}</span>
        <span>{s.step}</span>
      </div>

      {/* Description */}
      <div style={{ padding: "16px 14px 0" }}>
        <p style={{ fontSize: 13, lineHeight: 1.7, color: "#71717A", margin: 0, fontFamily: "inherit" }}>
          {s.desc}
        </p>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: BORDER_BRIGHT, margin: "16px 0 0" }} />

      {/* Stat blocks row */}
      <div style={{ display: "flex" }}>
        {s.stats.map((stat, i) => (
          <div key={i} style={{
            flex: 1,
            padding: "16px 20px",
            background: "#0C0C0E",
            borderRight: i < s.stats.length - 1 ? `1px solid ${BORDER}` : "none",
            borderRadius: 0,
          }}>
            <div style={{
              fontSize: 10, letterSpacing: "0.12em", color: "#3F3F46",
              textTransform: "uppercase", marginBottom: 8, fontFamily: "inherit",
            }}>
              {stat.key}
            </div>
            <div style={{
              fontSize: 28, fontWeight: 700, color: stat.color,
              fontFamily: "inherit", lineHeight: 1,
            }}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ProcessSection() {
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const children = entry.target.querySelectorAll<HTMLElement>("[data-anim]");
            children.forEach((child, i) => {
              setTimeout(() => {
                child.style.opacity = "1";
                child.style.transform = "translateY(0)";
                child.style.transition = "opacity 0.6s ease, transform 0.6s ease, border-color 0.2s, border-left-color 0.2s";
              }, i * 120);
            });
          }
        });
      },
      { threshold: 0.1 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} style={{
      padding: "80px 24px",
      maxWidth: 680,
      margin: "0 auto",
      borderTop: `1px solid ${BORDER_SECTION}`,
    }}>
      <div data-anim style={{ opacity: 0, transform: "translateY(16px)", transition: "all 0.6s ease", marginBottom: 40 }}>
        <div style={{ fontSize: 11, letterSpacing: "0.12em", color: "#3F3F46", marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>
          {"// 01_process"}
        </div>
        <h2 style={{
          fontSize: "clamp(24px, 3vw, 36px)", fontWeight: 600, letterSpacing: "-0.02em",
          color: "#E4E4E7", margin: 0, fontFamily: "'JetBrains Mono', monospace",
        }}>
          observe. reason. act.
        </h2>
      </div>

      {steps.map((s, i) => (
        <NotebookCell key={i} s={s} />
      ))}
    </section>
  );
}
