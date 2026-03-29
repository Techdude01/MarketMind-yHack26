"use client";

import { useEffect, useRef } from "react";
import { MM, type PnLPoint } from "./mock-data";

function formatUsd(n: number): string {
  const prefix = n >= 0 ? "+" : "";
  return `${prefix}$${Math.abs(n).toFixed(2)}`;
}

export default function PnLChart({ points }: { points: PnLPoint[] }) {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.querySelectorAll<HTMLElement>("[data-anim]").forEach((el, i) => {
              setTimeout(() => { el.style.opacity = "1"; el.style.transform = "translateY(0)"; }, i * 80);
            });
          }
        });
      },
      { threshold: 0.1 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const total   = points[points.length - 1]?.cumulative ?? 0;
  const bestDay = Math.max(...points.map((p) => p.daily));
  const worstDay= Math.min(...points.map((p) => p.daily));

  // SVG polyline for cumulative line
  const svgW = 800, svgH = 120;
  const vals  = points.map((p) => p.cumulative);
  const minV  = Math.min(...vals);
  const maxV  = Math.max(...vals);
  const range = maxV - minV || 1;
  const polyline = vals
    .map((v, i) => `${(i / (vals.length - 1)) * svgW},${svgH - ((v - minV) / range) * (svgH - 12) - 6}`)
    .join(" ");

  // Bar chart for daily
  const maxAbs = Math.max(...points.map((p) => Math.abs(p.daily)), 1);
  const barW   = 14;
  const barGap = 2;
  const barAreaH = 48;

  const finalColor = total >= 0 ? MM.green : MM.red;

  return (
    <div ref={sectionRef} style={{ border: `1px solid ${MM.border}`, background: MM.surface, borderRadius: 0, overflow: "hidden", fontFamily: MM.font }}>
      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "8px 16px", borderBottom: `1px solid ${MM.border}`,
        fontSize: 11, letterSpacing: "0.12em", color: MM.ghost,
      }}>
        <span>PNL_OVERVIEW</span>
        <span>30d window</span>
      </div>

      {/* Stat strip */}
      <div data-anim style={{ opacity: 0, transform: "translateY(10px)", transition: "all 0.5s ease", display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 1, background: MM.border }}>
        {[
          { label: "TOTAL_PNL",  value: formatUsd(total),    color: finalColor },
          { label: "BEST_DAY",   value: formatUsd(bestDay),  color: MM.green },
          { label: "WORST_DAY",  value: formatUsd(worstDay), color: MM.red },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ background: MM.surface, padding: "14px 16px" }}>
            <div style={{ fontSize: 10, letterSpacing: "0.12em", color: MM.ghost, marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color, fontFamily: MM.font }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Cumulative polyline */}
      <div data-anim style={{ opacity: 0, transform: "translateY(10px)", transition: "all 0.5s ease 0.1s", padding: "16px 16px 8px" }}>
        <div style={{ fontSize: 10, letterSpacing: "0.12em", color: MM.ghost, marginBottom: 8 }}>CUMULATIVE_PNL</div>
        <svg width="100%" viewBox={`0 0 ${svgW} ${svgH}`} preserveAspectRatio="none" style={{ display: "block", height: svgH }}>
          {/* Zero line */}
          {(() => {
            const zeroY = svgH - ((0 - minV) / range) * (svgH - 12) - 6;
            return <line x1="0" y1={zeroY} x2={svgW} y2={zeroY} stroke={MM.ghost} strokeWidth="0.5" strokeDasharray="4 4" />;
          })()}
          <polyline points={polyline} fill="none" stroke={finalColor} strokeWidth="1.5" />
        </svg>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 10, color: MM.ghost }}>
          <span>{points[0]?.date}</span>
          <span>{points[14]?.date}</span>
          <span>{points[29]?.date}</span>
        </div>
      </div>

      {/* Daily bar chart */}
      <div data-anim style={{ opacity: 0, transform: "translateY(10px)", transition: "all 0.5s ease 0.2s", padding: "0 16px 16px" }}>
        <div style={{ fontSize: 10, letterSpacing: "0.12em", color: MM.ghost, marginBottom: 8 }}>DAILY_PNL</div>
        <svg
          width="100%"
          viewBox={`0 0 ${points.length * (barW + barGap)} ${barAreaH}`}
          preserveAspectRatio="none"
          style={{ display: "block", height: barAreaH }}
        >
          {points.map((p, i) => {
            const barH = Math.max(2, (Math.abs(p.daily) / maxAbs) * (barAreaH / 2 - 2));
            const isPos = p.daily >= 0;
            const mid = barAreaH / 2;
            return (
              <rect
                key={i}
                x={i * (barW + barGap)}
                y={isPos ? mid - barH : mid}
                width={barW}
                height={barH}
                fill={isPos ? MM.green : MM.red}
                opacity="0.7"
              />
            );
          })}
          {/* Mid line */}
          <line x1="0" y1={barAreaH / 2} x2={points.length * (barW + barGap)} y2={barAreaH / 2} stroke={MM.ghost} strokeWidth="0.5" />
        </svg>
      </div>
    </div>
  );
}
