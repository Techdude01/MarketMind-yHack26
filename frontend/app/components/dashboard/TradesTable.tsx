"use client";

import { useEffect, useRef, useState } from "react";
import { MM, type Trade } from "./mock-data";

type SortKey = "market" | "side" | "quantity" | "entryPrice" | "pnl" | "openedAt";

function pnlColor(pnl: number | null, status: Trade["status"]): string {
  if (status === "open") return MM.dim;
  if (pnl === null) return MM.dim;
  return pnl >= 0 ? MM.green : MM.red;
}

function StatusBadge({ status }: { status: Trade["status"] }) {
  const colors: Record<Trade["status"], { color: string; border: string }> = {
    open: { color: MM.dim,   border: MM.border },
    won:  { color: MM.green, border: MM.green },
    lost: { color: MM.red,   border: MM.red },
  };
  const { color, border } = colors[status] || { color: MM.dim, border: MM.border };
  return (
    <span style={{ fontSize: 10, letterSpacing: "0.1em", color, border: `1px solid ${border}`, padding: "2px 6px" }}>
      {status ? status.toUpperCase() : "UNKNOWN"}
    </span>
  );
}

export default function TradesTable({ trades }: { trades: Trade[] }) {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [sortKey, setSortKey]   = useState<SortKey>("openedAt");
  const [sortDir, setSortDir]   = useState<1 | -1>(-1);
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.querySelectorAll<HTMLElement>("[data-anim]").forEach((el, i) => {
              setTimeout(() => { el.style.opacity = "1"; el.style.transform = "translateY(0)"; }, i * 40);
            });
          }
        });
      },
      { threshold: 0.05 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) setSortDir((d) => (d === 1 ? -1 : 1));
    else { setSortKey(key); setSortDir(-1); }
  };

  const sorted = [...trades].sort((a, b) => {
    const av = a[sortKey] ?? (sortKey === "pnl" ? -Infinity : "");
    const bv = b[sortKey] ?? (sortKey === "pnl" ? -Infinity : "");
    return av < bv ? -sortDir : av > bv ? sortDir : 0;
  });

  const cols: { key: SortKey | null; label: string; align: "left" | "right" | "center" }[] = [
    { key: "market",     label: "MARKET",       align: "left" },
    { key: "side",       label: "SIDE",         align: "center" },
    { key: "quantity",   label: "QTY",          align: "right" },
    { key: "entryPrice", label: "ENTRY",        align: "right" },
    { key: null,         label: "EXIT",         align: "right" },
    { key: "pnl",        label: "P&L",          align: "right" },
    { key: null,         label: "STATUS",       align: "center" },
    { key: "openedAt",   label: "OPENED",       align: "right" },
  ];

  const thStyle: React.CSSProperties = {
    padding: "8px 12px", fontSize: 10, letterSpacing: "0.12em",
    color: MM.ghost, fontWeight: 400, whiteSpace: "nowrap",
    cursor: "pointer", userSelect: "none", background: MM.bg,
    border: `1px solid ${MM.border}`, borderTop: "none", borderLeft: "none",
  };

  return (
    <div ref={sectionRef} style={{ border: `1px solid ${MM.border}`, background: MM.surface, borderRadius: 0, overflow: "hidden", fontFamily: MM.font }}>
      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "8px 16px", borderBottom: `1px solid ${MM.border}`,
        fontSize: 11, letterSpacing: "0.12em", color: MM.ghost,
      }}>
        <span>TRADE_HISTORY</span>
        <span>{trades.length} trades</span>
      </div>

      {/* Scrollable table wrapper */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr>
              {cols.map(({ key, label, align }) => (
                <th
                  key={label}
                  onClick={() => key && handleSort(key)}
                  style={{ ...thStyle, textAlign: align, cursor: key ? "pointer" : "default" }}
                  onMouseEnter={(e) => key && (e.currentTarget.style.color = MM.green)}
                  onMouseLeave={(e) => (e.currentTarget.style.color = MM.ghost)}
                >
                  {label}
                  {key && sortKey === key ? (sortDir === 1 ? " ↑" : " ↓") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((t, idx) => {
              const isHovered = hoveredRow === t.id;
              const pnlStr = t.pnl === null ? "—" : `${t.pnl >= 0 ? "+" : ""}$${Math.abs(t.pnl).toFixed(2)}`;
              return (
                <tr
                  key={t.id}
                  data-anim
                  onMouseEnter={() => setHoveredRow(t.id)}
                  onMouseLeave={() => setHoveredRow(null)}
                  style={{
                    opacity: 0,
                    transform: "translateY(8px)",
                    transition: "all 0.4s ease, background 0.15s",
                    background: isHovered ? "rgba(74,222,128,0.04)" : idx % 2 === 0 ? MM.surface : MM.bg,
                    borderLeft: `2px solid ${isHovered ? MM.green : "transparent"}`,
                  }}
                >
                  <td style={{ padding: "10px 12px", color: MM.text, whiteSpace: "nowrap", borderBottom: `1px solid ${MM.border}` }}>
                    {t.market}
                  </td>
                  <td style={{ padding: "10px 12px", textAlign: "center", borderBottom: `1px solid ${MM.border}` }}>
                    <span style={{ color: t.side === "YES" ? MM.green : MM.red, fontWeight: 500 }}>{t.side}</span>
                  </td>
                  <td style={{ padding: "10px 12px", textAlign: "right", color: MM.dim, borderBottom: `1px solid ${MM.border}` }}>
                    {t.quantity}
                  </td>
                  <td style={{ padding: "10px 12px", textAlign: "right", color: MM.text, borderBottom: `1px solid ${MM.border}` }}>
                    {t.entryPrice.toFixed(3)}
                  </td>
                  <td style={{ padding: "10px 12px", textAlign: "right", color: MM.dim, borderBottom: `1px solid ${MM.border}` }}>
                    {t.exitPrice?.toFixed(3) ?? "—"}
                  </td>
                  <td style={{ padding: "10px 12px", textAlign: "right", fontWeight: 600, color: pnlColor(t.pnl, t.status), borderBottom: `1px solid ${MM.border}` }}>
                    {pnlStr}
                  </td>
                  <td style={{ padding: "10px 12px", textAlign: "center", borderBottom: `1px solid ${MM.border}` }}>
                    <StatusBadge status={t.status} />
                  </td>
                  <td style={{ padding: "10px 12px", textAlign: "right", color: MM.ghost, whiteSpace: "nowrap", borderBottom: `1px solid ${MM.border}` }}>
                    {t.openedAt}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
