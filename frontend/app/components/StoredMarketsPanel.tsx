"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:5001";

// ── Design tokens ───────────────────────────────────────────
const MM = {
  bg:          "#0C0C0E",
  surface:     "#16161A",
  border:      "rgba(255,255,255,0.18)",
  borderBright:"rgba(255,255,255,0.32)",
  text:        "#E4E4E7",
  dim:         "#71717A",
  ghost:       "#3F3F46",
  green:       "#4ADE80",
  red:         "#F87171",
  font:        "'JetBrains Mono', monospace",
};

export type DbMarket = {
  polymarket_id: number;
  slug: string | null;
  question: string;
  description: string | null;
  image_url: string | null;
  end_date: string | null;
  active: boolean | null;
  closed: boolean | null;
  featured: boolean | null;
  last_trade_price: number | null;
  best_bid: number | null;
  best_ask: number | null;
  volume: number | null;
  volume_num: number | null;
  liquidity: number | null;
  outcomes: unknown;
  outcome_prices: unknown;
  updated_at_api: string | null;
  last_ingested_at: string | null;
};

function formatUsd(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

function formatPrice(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toFixed(3);
}

function formatEndDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

type Props = {
  title?: string;
};

export function StoredMarketsPanel({ title = "Markets" }: Props) {
  const [markets, setMarkets] = useState<DbMarket[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  const loadMarkets = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/markets/homepage`);
      const body: unknown = await res.json().catch(() => ({}));
      if (!res.ok) {
        const err =
          typeof body === "object" &&
          body !== null &&
          "error" in body &&
          typeof (body as { error: unknown }).error === "string"
            ? (body as { error: string }).error
            : `HTTP ${res.status}`;
        setError(err);
        setMarkets([]);
        return;
      }
      const list =
        typeof body === "object" &&
        body !== null &&
        "markets" in body &&
        Array.isArray((body as { markets: unknown }).markets)
          ? (body as { markets: DbMarket[] }).markets
          : [];
      setMarkets(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setMarkets([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMarkets();
  }, [loadMarkets]);

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", padding: "32px 24px", fontFamily: MM.font }}>
      {/* ── Header ── */}
      <div style={{ marginBottom: 32, display: "flex", flexWrap: "wrap", alignItems: "flex-end", justifyContent: "space-between", gap: 16 }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: "0.12em", color: MM.ghost, marginBottom: 8 }}>// _markets</div>
          <h1 style={{ fontSize: "clamp(20px, 3vw, 28px)", fontWeight: 700, color: MM.text, margin: 0, letterSpacing: "-0.02em" }}>
            {title}
          </h1>
          <p style={{ marginTop: 6, fontSize: 12, color: MM.dim, maxWidth: 480 }}>
            Curated homepage markets ranked by volume and activity.
          </p>
        </div>
      </div>

      {/* ── Status messages ── */}
      {error ? (
        <div style={{ marginBottom: 16, border: `1px solid ${MM.red}`, background: "rgba(248,113,113,0.06)", padding: "10px 14px", fontSize: 12, color: MM.red }}>
          error: {error}
        </div>
      ) : null}
      {loading && markets.length === 0 ? (
        <div style={{ fontSize: 12, color: MM.dim }}>fetching markets...</div>
      ) : null}
      {!loading && markets.length === 0 && !error ? (
        <div style={{ fontSize: 12, color: MM.ghost }}>
          no markets available yet.
        </div>
      ) : null}

      {/* ── Market grid ── */}
      {markets.length > 0 ? (
        <ul style={{ display: "grid", gap: 2, gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", listStyle: "none", padding: 0, margin: 0 }}>
          {markets.map((m) => (
            <MarketCard key={m.polymarket_id} m={m} />
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function MarketCard({ m }: { m: DbMarket }) {
  const router = useRouter();
  const [hovered, setHovered] = useState(false);

  const handleClick = () => router.push(`/markets/${m.polymarket_id}`);
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") handleClick();
  };

  return (
    <li
      role="button"
      tabIndex={0}
      aria-label={m.question}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        border: `1px solid ${hovered ? MM.borderBright : MM.border}`,
        borderLeft: `2px solid ${hovered ? MM.green : "transparent"}`,
        background: MM.surface,
        borderRadius: 0,
        transition: "border-color 0.2s, border-left-color 0.2s",
        cursor: "pointer",
      }}
    >
      {/* Image */}
      <div style={{ aspectRatio: "2/1", width: "100%", background: "#111114", position: "relative", overflow: "hidden" }}>
        {m.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={m.image_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", fontSize: 11, color: MM.ghost }}>
            no_image
          </div>
        )}
      </div>
      {/* Body */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8, padding: 14 }}>
        <p style={{ fontSize: 12, fontWeight: 500, color: MM.text, margin: 0, lineHeight: 1.6 }}>
          {m.question}
        </p>
        {/* Badges */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {m.active && (
            <span style={{ fontSize: 10, letterSpacing: "0.1em", color: MM.green, border: `1px solid ${MM.green}`, padding: "2px 6px" }}>
              ACTIVE
            </span>
          )}
          {m.closed && (
            <span style={{ fontSize: 10, letterSpacing: "0.1em", color: MM.ghost, border: `1px solid ${MM.border}`, padding: "2px 6px" }}>
              CLOSED
            </span>
          )}
          {m.featured && (
            <span style={{ fontSize: 10, letterSpacing: "0.1em", color: "#FCD34D", border: "1px solid rgba(252,211,77,0.4)", padding: "2px 6px" }}>
              FEATURED
            </span>
          )}
        </div>
        {/* Stats */}
        <dl style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 8px", fontSize: 11, margin: 0 }}>
          <dt style={{ color: MM.ghost }}>volume</dt>
          <dd style={{ textAlign: "right", color: MM.text, margin: 0 }}>{formatUsd(m.volume_num ?? m.volume ?? null)}</dd>
          <dt style={{ color: MM.ghost }}>last_trade</dt>
          <dd style={{ textAlign: "right", color: MM.text, margin: 0 }}>{formatPrice(m.last_trade_price)}</dd>
          <dt style={{ color: MM.ghost }}>ends</dt>
          <dd style={{ textAlign: "right", color: MM.dim, margin: 0 }}>{formatEndDate(m.end_date)}</dd>
        </dl>
      </div>
    </li>
  );
}
