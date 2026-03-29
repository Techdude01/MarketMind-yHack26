
"use client";

import { useEffect, useState } from "react";
import Nav from "../components/landing/Nav";
import UserInfoCard from "../components/dashboard/UserInfoCard";
import PnLChart from "../components/dashboard/PnLChart";
import TradesTable from "../components/dashboard/TradesTable";
import { MOCK_USER, MOCK_PNL } from "../components/dashboard/mock-data";

const NOISE_SVG = `<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'>
  <filter id='noise'><feTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='4' stitchTiles='stitch'/>
  <feColorMatrix type='saturate' values='0'/></filter>
  <rect width='200' height='200' filter='url(#noise)' opacity='1' fill='white'/></svg>`;
const noiseUrl = `url("data:image/svg+xml,${encodeURIComponent(NOISE_SVG)}")`;

type BackendTrade = {
  id: number;
  createdAt: string;
  conditionId: string;
  tokenId: string;
  side: "BUY" | "SELL";
  amountUsd: number;
  price: number;
  walletAddress: string;
  market?: string | null;
  quantity?: number | null;
  entryPrice?: number | null;
  exitPrice?: number | null;
  status?: "OPEN" | "CLOSED" | null;
  pnl?: number | null;
  openedAt?: string | null;
  closedAt?: string | null;
};

type BackendTradesResponse = {
  ok: boolean;
  data: BackendTrade[];
};

function fmt(n: number | null | undefined, digits = 4) {
  if (n === null || n === undefined) return "—";
  return Number(n).toFixed(digits);
}

async function getTradesForDashboard() {
  const base =
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
    "http://localhost:5001";

  try {
    const res = await fetch(`${base}/api/trades/mock`, { cache: "no-store" });
    if (!res.ok) return [];
    const json = (await res.json()) as BackendTradesResponse;
    if (!json?.ok || !Array.isArray(json.data)) return [];

    return json.data.map((t) => ({
      id: t.id,
      market: t.market || `${t.conditionId.slice(0, 10)}...`,
      side: t.side,
      quantity: Number(t.quantity ?? t.amountUsd ?? 0),
      entryPrice: Number(t.entryPrice ?? t.price ?? 0),
      exitPrice:
        t.exitPrice === null || t.exitPrice === undefined
          ? null
          : Number(t.exitPrice),
      status: (t.status ?? "OPEN") as "OPEN" | "CLOSED",
      pnl: Number(t.pnl ?? 0),
      createdAt: t.openedAt ?? t.createdAt,
      updatedAt: t.closedAt ?? t.createdAt,

      size: `$${fmt(Number(t.quantity ?? t.amountUsd ?? 0), 2)}`,
      price: fmt(Number(t.entryPrice ?? t.price ?? 0), 4),
      time: new Date(t.openedAt ?? t.createdAt).toLocaleString(),
      tokenId: t.tokenId,
      walletAddress: t.walletAddress,
    }));
  } catch {
    return [];
  }
}


export default function DashboardPage() {
  const [wallet, setWallet] = useState<string | null>(null);
  const [disconnected, setDisconnected] = useState<boolean>(false);
  const [trades, setTrades] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      // Check disconnect flag
      if (sessionStorage.getItem("wallet_disconnected")) {
        setDisconnected(true);
        setWallet(null);
        return;
      }
      // Detect wallet
      const eth = (window as any).ethereum;
      if (!eth) {
        setWallet(null);
        return;
      }
      eth.request({ method: "eth_accounts" }).then((accounts: string[]) => {
        const addr = accounts?.[0] || null;
        setWallet(addr);
        if (addr) {
          setLoading(true);
          getTradesForDashboard()
            .then(setTrades)
            .finally(() => setLoading(false));
        }
      });
    }
  }, []);

  if (!wallet || disconnected) {
    return (
      <div
        style={{
          background: "#0C0C0E",
          minHeight: "100vh",
          color: "#E4E4E7",
          fontFamily: "'JetBrains Mono', monospace",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Nav />
        <div style={{ marginTop: 120, textAlign: "center" }}>
          <h2 style={{ fontSize: 22, fontWeight: 600, color: "#4ADE80" }}>
            Connect your wallet to view your dashboard
          </h2>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        background: "#0C0C0E",
        minHeight: "100vh",
        color: "#E4E4E7",
        fontFamily: "'JetBrains Mono', monospace",
        position: "relative",
      }}
    >
      <div
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 9999,
          pointerEvents: "none",
          backgroundImage: noiseUrl,
          backgroundRepeat: "repeat",
          backgroundSize: "200px 200px",
          opacity: 0.14,
          mixBlendMode: "screen",
        }}
        aria-hidden="true"
      />

      <Nav />

      <main style={{ paddingTop: 48 }}>
        <div
          style={{ maxWidth: 1000, margin: "0 auto", padding: "40px 24px 0" }}
        >
          <div
            style={{
              fontSize: 11,
              letterSpacing: "0.12em",
              color: "#3F3F46",
              marginBottom: 8,
            }}
          >
            // _dashboard
          </div>
          <h1
            style={{
              fontSize: "clamp(22px, 3vw, 32px)",
              fontWeight: 700,
              color: "#E4E4E7",
              margin: 0,
              letterSpacing: "-0.02em",
            }}
          >
            agent_portfolio
          </h1>
          <p style={{ fontSize: 12, color: "#71717A", marginTop: 8 }}>
            mock trades loaded from backend
          </p>
        </div>

        <div
          style={{
            maxWidth: 1000,
            margin: "0 auto",
            padding: "24px 24px 80px",
            display: "flex",
            flexDirection: "column",
            gap: 2,
          }}
        >
          <UserInfoCard user={MOCK_USER} />
          <PnLChart points={MOCK_PNL} />
          {loading ? (
            <div style={{ textAlign: "center", margin: "32px 0", color: "#4ADE80", fontSize: 18 }}>
              Loading trades…
            </div>
          ) : (
            <TradesTable trades={trades as any} />
          )}
        </div>
      </main>
    </div>
  );
}
