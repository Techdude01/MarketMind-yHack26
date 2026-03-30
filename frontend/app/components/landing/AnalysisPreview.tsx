"use client";

import { useEffect, useRef } from "react";

const BORDER         = "rgba(255,255,255,0.18)";
const BORDER_BRIGHT  = "rgba(255,255,255,0.32)";
const BORDER_SECTION = "rgba(255,255,255,0.22)";

const mono = "'JetBrains Mono', monospace";

const probCurve = () => {
  const pts: number[] = [];
  let v = 0.45;
  for (let i = 0; i < 60; i++) {
    v += (Math.random() - 0.46) * 0.03;
    v = Math.max(0.2, Math.min(0.9, v));
    pts.push(v);
  }
  return pts;
};

function StatCell({ label: lbl, value }: { label: string; value: string }) {
  return (
    <div style={{
      background: "#16161A", border: `1px solid ${BORDER}`, borderRadius: 0,
      padding: "12px 14px", marginBottom: 1,
    }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = BORDER_BRIGHT)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = BORDER)}
    >
      <div style={{ fontSize: 11, letterSpacing: "0.12em", color: "#3F3F46", marginBottom: 6 }}>{lbl}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: "#4ADE80", fontFamily: mono }}>{value}</div>
    </div>
  );
}

export default function AnalysisPreview() {
  const sectionRef = useRef<HTMLElement>(null);
  const pts = useRef(probCurve());

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
              }, i * 100);
            });
          }
        });
      },
      { threshold: 0.1 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const svgW = 400, svgH = 160;
  const polyline = pts.current
    .map((p, i) => `${(i / (pts.current.length - 1)) * svgW},${svgH - p * svgH}`)
    .join(" ");

  return (
    <section ref={sectionRef} style={{
      padding: "80px 24px",
      maxWidth: 1000,
      margin: "0 auto",
      borderTop: `1px solid ${BORDER_SECTION}`,
    }}>
      <div data-anim style={{ opacity: 0, transform: "translateY(16px)", transition: "all 0.6s ease", marginBottom: 32 }}>
        <div style={{ fontSize: 11, letterSpacing: "0.12em", color: "#3F3F46", marginBottom: 12 }}>
          {"// 03_analysis_view"}
        </div>
        <h2 style={{
          fontSize: "clamp(24px, 3vw, 36px)", fontWeight: 600, letterSpacing: "-0.02em",
          color: "#E4E4E7", fontFamily: mono, margin: 0,
        }}>
          a bloomberg terminal. startup speed.
        </h2>
      </div>

      {/* Terminal Frame */}
      <div data-anim style={{
        border: `1px solid ${BORDER}`, borderRadius: 0, background: "#0C0C0E", overflow: "hidden",
        opacity: 0, transform: "translateY(16px)", transition: "all 0.6s ease",
      }}
        onMouseEnter={(e) => (e.currentTarget.style.borderColor = BORDER_BRIGHT)}
        onMouseLeave={(e) => (e.currentTarget.style.borderColor = BORDER)}
      >
        {/* Title bar */}
        <div style={{
          display: "flex", alignItems: "center", gap: 8, padding: "10px 14px",
          borderBottom: `1px solid ${BORDER}`, fontSize: 12, color: "#3F3F46",
        }}>
          <span>● ● ●</span>
          <span style={{ color: "#71717A", marginLeft: 8 }}>~/marketmind/market/trump-nh-2024</span>
        </div>

        {/* Inner grid */}
        <div style={{
          display: "grid", gridTemplateColumns: "200px 1fr 200px", minHeight: 300,
        }}>
          {/* Left panel */}
          <div style={{ borderRight: `1px solid ${BORDER}`, padding: 20, display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div style={{ fontSize: 13, color: "#71717A", lineHeight: 1.7, marginBottom: 20, fontFamily: mono }}>
              Will Trump win the New Hampshire primary?
            </div>
            <div style={{ fontSize: "clamp(36px, 4vw, 52px)", fontWeight: 700, color: "#4ADE80", fontFamily: mono, lineHeight: 1 }}>
              0.73
            </div>
            <div style={{ fontSize: 11, letterSpacing: "0.12em", color: "#3F3F46", marginTop: 6 }}>
              IMPLIED_PROBABILITY
            </div>
          </div>

          {/* Center panel — chart */}
          <div style={{ borderRight: `1px solid ${BORDER}`, padding: 20, display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <svg width="100%" viewBox={`0 0 ${svgW} ${svgH}`} preserveAspectRatio="none" style={{ display: "block" }}>
              <polyline points={polyline} fill="none" stroke="#4ADE80" strokeWidth="1.5" />
            </svg>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 10, color: "#3F3F46", fontFamily: mono }}>
              <span>30d ago</span><span>15d</span><span>now</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 10, color: "#3F3F46", fontFamily: mono }}>
              <span>0.00</span><span>0.50</span><span>1.00</span>
            </div>
          </div>

          {/* Right panel — stats */}
          <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 0 }}>
            <StatCell label="CURRENT_ODDS" value="0.73" />
            <StatCell label="AGENT_PROB" value="0.81" />
            <StatCell label="EXPECTED_VALUE" value="+$0.22" />
          </div>
        </div>

        {/* Bottom — thesis */}
        <div style={{ borderTop: `1px solid ${BORDER}` }}>
          <div style={{
            padding: "8px 14px", borderBottom: `1px solid ${BORDER}`,
            fontSize: 11, letterSpacing: "0.12em", color: "#3F3F46",
          }}>
            [AGENT_THESIS]
          </div>
          <pre style={{
            padding: "14px", fontSize: 12, lineHeight: 1.8, color: "#71717A",
            margin: 0, fontFamily: mono, whiteSpace: "pre-wrap",
          }}>
{`Market prices Trump NH at 73% but agent analysis of polling data,\nendorsement patterns, and historical NH primary dynamics suggests 81%.\nKey divergence driver: late-deciding independents historically break\ntoward frontrunner at +8-12% in final 72 hours.`}
            <span style={{
              display: "inline-block", width: 8, height: 14, background: "#4ADE80",
              marginLeft: 4, verticalAlign: "middle",
              animation: "mmBlink 1s step-end infinite",
            }} />
          </pre>
          <style>{`@keyframes mmBlink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
        </div>
      </div>
    </section>
  );
}
