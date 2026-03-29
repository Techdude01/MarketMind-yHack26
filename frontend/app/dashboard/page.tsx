import Nav from "../components/landing/Nav";
import UserInfoCard from "../components/dashboard/UserInfoCard";
import PnLChart from "../components/dashboard/PnLChart";
import TradesTable from "../components/dashboard/TradesTable";
import { MOCK_USER, MOCK_TRADES, MOCK_PNL } from "../components/dashboard/mock-data";

// Inline SVG noise (same as landing)
const NOISE_SVG = `<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'>
  <filter id='noise'><feTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='4' stitchTiles='stitch'/>
  <feColorMatrix type='saturate' values='0'/></filter>
  <rect width='200' height='200' filter='url(#noise)' opacity='1' fill='white'/></svg>`;
const noiseUrl = `url("data:image/svg+xml,${encodeURIComponent(NOISE_SVG)}")`;

export default function DashboardPage() {
  return (
    <div style={{ background: "#0C0C0E", minHeight: "100vh", color: "#E4E4E7", fontFamily: "'JetBrains Mono', monospace", position: "relative" }}>
      {/* Film grain overlay */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 9999, pointerEvents: "none",
        backgroundImage: noiseUrl, backgroundRepeat: "repeat", backgroundSize: "200px 200px",
        opacity: 0.14, mixBlendMode: "screen",
      }} aria-hidden="true" />

      <Nav />

      <main style={{ paddingTop: 48 }}>
        {/* Section header */}
        <div style={{ maxWidth: 1000, margin: "0 auto", padding: "40px 24px 0" }}>
          <div style={{ fontSize: 11, letterSpacing: "0.12em", color: "#3F3F46", marginBottom: 8 }}>
            // _dashboard
          </div>
          <h1 style={{ fontSize: "clamp(22px, 3vw, 32px)", fontWeight: 700, color: "#E4E4E7", margin: 0, letterSpacing: "-0.02em" }}>
            agent_portfolio
          </h1>
          <p style={{ fontSize: 12, color: "#71717A", marginTop: 8 }}>
            mock data · connect backend for live positions
          </p>
        </div>

        {/* Dashboard sections */}
        <div style={{ maxWidth: 1000, margin: "0 auto", padding: "24px 24px 80px", display: "flex", flexDirection: "column", gap: 2 }}>
          <UserInfoCard user={MOCK_USER} />
          <PnLChart points={MOCK_PNL} />
          <TradesTable trades={MOCK_TRADES} />
        </div>
      </main>
    </div>
  );
}
