"use client";

import { useEffect, useRef } from "react";

const BORDER         = "rgba(255,255,255,0.18)";
const BORDER_BRIGHT  = "rgba(255,255,255,0.32)";
const BORDER_SECTION = "rgba(255,255,255,0.22)";

const sparklinePoints = () => {
  const pts: number[] = [];
  let v = 0.3;
  for (let i = 0; i < 30; i++) {
    v += (Math.random() - 0.48) * 0.06;
    v = Math.max(0.1, Math.min(0.9, v));
    pts.push(v);
  }
  return pts;
};

function Sparkline({ points, width = 200, height = 60 }: { points: number[]; width?: number; height?: number }) {
  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ display: "block" }}>
      <polyline
        points={points.map((p, i) => `${(i / (points.length - 1)) * width},${height - p * height}`).join(" ")}
        fill="none" stroke="#4ADE80" strokeWidth="1.5"
      />
    </svg>
  );
}

const cell: React.CSSProperties = {
  background: "#16161A",
  border: `1px solid ${BORDER}`,
  borderRadius: 0,
  padding: 20,
  fontFamily: "'JetBrains Mono', monospace",
  display: "flex",
  flexDirection: "column",
  justifyContent: "space-between",
  minHeight: 0,
};

const labelStyle: React.CSSProperties = { fontSize: 11, letterSpacing: "0.12em", color: "#3F3F46", marginBottom: 8 };

const bigNum = (c?: string): React.CSSProperties => ({
  fontSize: "clamp(36px, 4vw, 64px)", fontWeight: 700,
  color: c || "#E4E4E7", lineHeight: 1, fontFamily: "inherit",
});

const medNum = (c?: string): React.CSSProperties => ({
  fontSize: "clamp(24px, 3vw, 40px)", fontWeight: 700,
  color: c || "#E4E4E7", lineHeight: 1, fontFamily: "inherit",
});

const logLines = [
  "[00:00:01] scanning 847 active markets...",
  "[00:00:03] news_context loaded (reuters, ap, bloomberg)",
  "[00:00:07] divergence detected: FED_CUTS_JUNE Δ+0.36",
  "[00:00:08] running thesis generation...",
  "[00:00:12] signal emitted → confidence=0.81",
  "[00:00:14] cycle complete. next in 23s.",
];

export default function MetricsGrid() {
  const sectionRef = useRef<HTMLElement>(null);
  const pts = useRef(sparklinePoints());

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
              }, i * 80);
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
      maxWidth: 1000,
      margin: "0 auto",
      borderTop: `1px solid ${BORDER_SECTION}`,
    }}>
      <div data-anim style={{ opacity: 0, transform: "translateY(16px)", transition: "all 0.6s ease", marginBottom: 32 }}>
        <div style={{ fontSize: 11, letterSpacing: "0.12em", color: "#3F3F46", marginBottom: 12 }}>
          {"// 02_signal_stats"}
        </div>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(12, 1fr)",
        gridTemplateRows: "220px 220px",
        gap: 1,
      }}>
        {/* Cell A: Divergence Score — 5 cols, full height */}
        <div data-anim style={{
          ...cell, gridColumn: "span 5", gridRow: "span 2",
          opacity: 0, transform: "translateY(16px)", transition: "all 0.6s ease",
        }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = BORDER_BRIGHT)}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = BORDER)}
        >
          <div>
            <div style={labelStyle}>DIVERGENCE_SCORE</div>
            <div style={bigNum("#4ADE80")}>0.36</div>
            <div style={{ fontSize: 12, color: "#71717A", marginTop: 8 }}>avg cross-market divergence</div>
          </div>
          <Sparkline points={pts.current} width={280} height={80} />
        </div>

        {/* Cell B: Markets Flagged — 4 cols top */}
        <div data-anim style={{
          ...cell, gridColumn: "span 4",
          opacity: 0, transform: "translateY(16px)", transition: "all 0.6s ease",
        }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = BORDER_BRIGHT)}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = BORDER)}
        >
          <div style={labelStyle}>MARKETS_FLAGGED_TODAY</div>
          <div style={medNum()}>23</div>
          <div style={{ fontSize: 11, color: "#3F3F46", marginTop: 8 }}>of 847 active</div>
        </div>

        {/* Cell C: Avg Confidence — 3 cols top */}
        <div data-anim style={{
          ...cell, gridColumn: "span 3",
          opacity: 0, transform: "translateY(16px)", transition: "all 0.6s ease",
        }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = BORDER_BRIGHT)}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = BORDER)}
        >
          <div style={labelStyle}>AVG_CONFIDENCE</div>
          <div style={medNum("#4ADE80")}>0.73</div>
        </div>

        {/* Cell D: Top Signal — 4 cols bottom */}
        <div data-anim style={{
          ...cell, gridColumn: "span 4",
          opacity: 0, transform: "translateY(16px)", transition: "all 0.6s ease",
        }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = BORDER_BRIGHT)}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = BORDER)}
        >
          <div style={labelStyle}>TOP_SIGNAL</div>
          <div style={{ fontSize: 13, color: "#E4E4E7", fontFamily: "inherit", lineHeight: 1.7 }}>
            FED_CUTS_JUNE · <span style={{ color: "#F87171" }}>NO</span> · <span style={{ color: "#4ADE80" }}>Δ+0.36</span>
          </div>
        </div>

        {/* Cell E: Agent Cycles — 3 cols bottom */}
        <div data-anim style={{
          ...cell, gridColumn: "span 3",
          opacity: 0, transform: "translateY(16px)", transition: "all 0.6s ease",
        }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = BORDER_BRIGHT)}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = BORDER)}
        >
          <div style={labelStyle}>AGENT_CYCLES</div>
          <div style={medNum()}>1,247</div>
        </div>
      </div>

      {/* Cell F: Agent Log — full width */}
      <div data-anim style={{
        ...cell, marginTop: 1, opacity: 0, transform: "translateY(16px)", transition: "all 0.6s ease",
        maxHeight: 180, overflow: "auto",
      }}
        onMouseEnter={(e) => (e.currentTarget.style.borderColor = BORDER_BRIGHT)}
        onMouseLeave={(e) => (e.currentTarget.style.borderColor = BORDER)}
      >
        <div style={labelStyle}>AGENT_RUN_LOG</div>
        <pre style={{
          fontSize: 12, lineHeight: 1.8, color: "#71717A", margin: 0,
          fontFamily: "inherit", whiteSpace: "pre-wrap",
        }}>
          {logLines.join("\n")}
        </pre>
      </div>
    </section>
  );
}
