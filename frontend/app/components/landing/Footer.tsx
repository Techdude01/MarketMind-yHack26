"use client";

export default function Footer() {
  return (
    <footer style={{
      borderTop: "1px solid rgba(255,255,255,0.22)",
      background: "#0C0C0E",
      padding: "20px 24px",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      flexWrap: "wrap",
      gap: 12,
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 12,
      color: "#3F3F46",
    }}>
      <span><span style={{ color: "#4ADE80" }}>[MM]</span> MarketMind</span>
      <span>all_systems=nominal · uptime=99.98%</span>
      <span>
        built for [HACKATHON] 2025 ·{" "}
        <span
          style={{ cursor: "pointer", transition: "color 0.2s" }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#4ADE80")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "#3F3F46")}
        >_github</span>
      </span>
    </footer>
  );
}
