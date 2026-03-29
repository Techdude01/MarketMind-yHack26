const signals = [
  { market: "TRUMP_WINS_NH", side: "YES", prob: "0.73", delta: "+0.08" },
  { market: "FED_CUTS_JUNE", side: "NO", prob: "0.69", delta: "-0.12" },
  { market: "BTC_100K_Q2", side: "YES", prob: "0.41", delta: "+0.03" },
  { market: "RECESSION_2025", side: "NO", prob: "0.58", delta: "-0.05" },
  { market: "AI_REGULATION_EU", side: "YES", prob: "0.82", delta: "+0.14" },
  { market: "SPOTIFY_IPO_RIVAL", side: "NO", prob: "0.23", delta: "-0.02" },
  { market: "CHINA_TAIWAN_2025", side: "NO", prob: "0.91", delta: "+0.01" },
  { market: "ETH_MERGE_V2", side: "YES", prob: "0.55", delta: "+0.07" },
];

function SignalItem({ s }: { s: typeof signals[0] }) {
  return (
    <span style={{ display: "inline-flex", gap: 6, alignItems: "center", whiteSpace: "nowrap", padding: "0 24px" }}>
      <span style={{ color: s.side === "YES" ? "#4ADE80" : "#F87171", fontWeight: 500 }}>{s.side}</span>
      <span style={{ color: "#71717A" }}>{s.prob}</span>
      <span style={{ color: "#3F3F46" }}>·</span>
      <span style={{ color: "#71717A" }}>{s.market}</span>
      <span style={{ color: "#3F3F46" }}>·</span>
      <span style={{ color: s.delta.startsWith("+") ? "#4ADE80" : "#F87171" }}>{"Δ"}{s.delta}</span>
    </span>
  );
}

export default function SignalStrip() {
  const doubled = [...signals, ...signals];

  return (
    <div style={{
      background: "#111114",
      borderTop: "1px solid rgba(255,255,255,0.22)",
      borderBottom: "1px solid rgba(255,255,255,0.22)",
      overflow: "hidden", position: "relative",
      fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
    }}>
      <style>{`
        @keyframes mmMarquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
      <div style={{
        display: "flex", alignItems: "center", height: 40,
        animation: "mmMarquee 40s linear infinite",
        width: "max-content",
      }}>
        {doubled.map((s, i) => <SignalItem key={i} s={s} />)}
      </div>
    </div>
  );
}
