"use client";

import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:5001";

// ── Design tokens ───────────────────────────────────────────────────────────
const MM = {
  bg: "#0C0C0E",
  surface: "#16161A",
  surface2: "#1C1C22",
  border: "rgba(255,255,255,0.10)",
  borderHover: "rgba(255,255,255,0.22)",
  text: "#E4E4E7",
  textSub: "#A1A1AA",
  dim: "#71717A",
  ghost: "#3F3F46",
  green: "#4ADE80",
  greenDim: "rgba(74,222,128,0.15)",
  red: "#F87171",
  redDim: "rgba(248,113,113,0.15)",
  amber: "#FBBF24",
  font: "'JetBrains Mono', monospace",
};

// ── Types ───────────────────────────────────────────────────────────────────

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
  demo_score: number | null;
};

type SortKey = "demo_score" | "volume" | "price";

// ── Helpers ─────────────────────────────────────────────────────────────────

function compactVol(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

function pct(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return `${Math.round(n * 100)}%`;
}

function divergenceColor(score: number | null): string {
  if (score == null) return MM.ghost;
  if (score >= 19) return MM.green;
  if (score >= 17) return MM.amber;
  return MM.dim;
}

function divergenceLabel(score: number | null): string {
  if (score == null) return "—";
  return score.toFixed(1);
}

function sortMarkets(markets: DbMarket[], key: SortKey): DbMarket[] {
  const copy = [...markets];
  switch (key) {
    case "demo_score":
      return copy.sort((a, b) => (b.demo_score ?? 0) - (a.demo_score ?? 0));
    case "volume":
      return copy.sort(
        (a, b) => (b.volume_num ?? b.volume ?? 0) - (a.volume_num ?? a.volume ?? 0)
      );
    case "price":
      return copy.sort(
        (a, b) =>
          Math.abs((b.last_trade_price ?? 0) - 0.5) -
          Math.abs((a.last_trade_price ?? 0) - 0.5)
      );
    default:
      return copy;
  }
}

// ── Main Panel ──────────────────────────────────────────────────────────────

export function StoredMarketsPanel() {
  const [markets, setMarkets] = useState<DbMarket[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("demo_score");

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

  const filtered = useMemo(() => {
    let list = markets;
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((m) => m.question.toLowerCase().includes(q));
    }
    return sortMarkets(list, sortKey);
  }, [markets, search, sortKey]);

  const featured = useMemo(() => filtered.slice(0, 5), [filtered]);
  const grid = useMemo(() => filtered.slice(5), [filtered]);

  return (
    <div style={{ maxWidth: 1320, margin: "0 auto", padding: "28px 24px 64px", fontFamily: MM.font }}>
      {/* ── Header ── */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: MM.text, margin: 0, letterSpacing: "-0.02em" }}>
          Markets
        </h1>
        <p style={{ marginTop: 4, fontSize: 13, color: MM.dim }}>
          AI-curated prediction markets ranked by tradability
        </p>
      </div>

      {/* ── Controls ── */}
      <div style={{
        display: "flex", flexWrap: "wrap", alignItems: "center", gap: 12,
        marginBottom: 28, paddingBottom: 16, borderBottom: `1px solid ${MM.border}`,
      }}>
        <div style={{ position: "relative", flex: "1 1 280px", maxWidth: 400 }}>
          <svg
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={MM.dim}
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)" }}
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Search markets..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: "100%", padding: "10px 12px 10px 36px",
              background: MM.surface, border: `1px solid ${MM.border}`,
              color: MM.text, fontSize: 13, fontFamily: MM.font,
              borderRadius: 8, outline: "none",
            }}
          />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, color: MM.dim }}>Sort:</span>
          {(
            [
              ["demo_score", "Signal"],
              ["volume", "Volume"],
              ["price", "Odds"],
            ] as [SortKey, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setSortKey(key)}
              style={{
                padding: "6px 14px", fontSize: 12, fontFamily: MM.font,
                border: `1px solid ${sortKey === key ? MM.green : MM.border}`,
                background: sortKey === key ? "rgba(74,222,128,0.08)" : "transparent",
                color: sortKey === key ? MM.green : MM.dim,
                borderRadius: 6, cursor: "pointer",
                transition: "all 0.15s",
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Status ── */}
      {error && (
        <div style={{
          marginBottom: 20, border: `1px solid ${MM.red}`,
          background: "rgba(248,113,113,0.06)", padding: "10px 14px",
          fontSize: 12, color: MM.red, borderRadius: 8,
        }}>
          {error}
        </div>
      )}
      {loading && markets.length === 0 && (
        <div style={{ fontSize: 13, color: MM.dim, padding: "40px 0", textAlign: "center" }}>
          Loading markets...
        </div>
      )}
      {!loading && markets.length === 0 && !error && (
        <div style={{ fontSize: 13, color: MM.ghost, padding: "40px 0", textAlign: "center" }}>
          No markets available yet.
        </div>
      )}

      {/* ── Featured Carousel ── */}
      {featured.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 12, color: MM.dim, marginBottom: 12, letterSpacing: "0.06em" }}>
            TRENDING
          </div>
          <FeaturedCarousel markets={featured} />
        </div>
      )}

      {/* ── Grid ── */}
      {grid.length > 0 && (
        <div>
          <div style={{ fontSize: 12, color: MM.dim, marginBottom: 12, letterSpacing: "0.06em" }}>
            ALL MARKETS
          </div>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(235px, 1fr))",
            gap: 12,
          }}>
            {grid.map((m) => (
              <MarketCard key={m.polymarket_id} m={m} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Featured Carousel ───────────────────────────────────────────────────────

function FeaturedCarousel({ markets }: { markets: DbMarket[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (dir: "left" | "right") => {
    const el = scrollRef.current;
    if (!el) return;
    const amount = 354;
    el.scrollBy({ left: dir === "left" ? -amount : amount, behavior: "smooth" });
  };

  return (
    <div>
      <div
        ref={scrollRef}
        style={{
          display: "flex", gap: 14, overflowX: "auto",
          scrollSnapType: "x mandatory", scrollbarWidth: "none",
          paddingBottom: 4,
        }}
      >
        {markets.map((m) => (
          <FeaturedCard key={m.polymarket_id} m={m} />
        ))}
      </div>
      {/* Arrows */}
      <div style={{ display: "flex", justifyContent: "center", gap: 16, marginTop: 14 }}>
        <button
          onClick={() => scroll("left")}
          aria-label="Scroll left"
          style={{
            width: 36, height: 36, borderRadius: 8,
            border: `1px solid ${MM.border}`, background: MM.surface,
            color: MM.dim, cursor: "pointer", display: "flex",
            alignItems: "center", justifyContent: "center",
            transition: "border-color 0.15s, color 0.15s",
            fontSize: 18, fontFamily: MM.font,
          }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = MM.green; e.currentTarget.style.color = MM.green; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = MM.border; e.currentTarget.style.color = MM.dim; }}
        >
          &#8592;
        </button>
        <button
          onClick={() => scroll("right")}
          aria-label="Scroll right"
          style={{
            width: 36, height: 36, borderRadius: 8,
            border: `1px solid ${MM.border}`, background: MM.surface,
            color: MM.dim, cursor: "pointer", display: "flex",
            alignItems: "center", justifyContent: "center",
            transition: "border-color 0.15s, color 0.15s",
            fontSize: 18, fontFamily: MM.font,
          }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = MM.green; e.currentTarget.style.color = MM.green; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = MM.border; e.currentTarget.style.color = MM.dim; }}
        >
          &#8594;
        </button>
      </div>
    </div>
  );
}

// ── Featured Card ───────────────────────────────────────────────────────────

function FeaturedCard({ m }: { m: DbMarket }) {
  const router = useRouter();
  const yesP = m.last_trade_price ?? 0;
  const noP = 1 - yesP;
  const vol = compactVol(m.volume_num ?? m.volume ?? null);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => router.push(`/markets/${m.polymarket_id}`)}
      onKeyDown={(e) => { if (e.key === "Enter") router.push(`/markets/${m.polymarket_id}`); }}
      style={{
        flex: "0 0 340px",
        scrollSnapAlign: "start",
        borderRadius: 12,
        overflow: "hidden",
        border: `1px solid ${MM.border}`,
        background: MM.surface,
        cursor: "pointer",
        transition: "border-color 0.2s, transform 0.2s",
        position: "relative",
      }}
    >
      {/* Image */}
      <div style={{ height: 160, position: "relative", overflow: "hidden" }}>
        {m.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={m.image_url} alt=""
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : (
          <div style={{ width: "100%", height: "100%", background: "#111114" }} />
        )}
        <div style={{
          position: "absolute", inset: 0,
          background: "linear-gradient(0deg, rgba(12,12,14,0.95) 0%, rgba(12,12,14,0.2) 50%, transparent 100%)",
        }} />
        {/* Signal badge */}
        <div style={{
          position: "absolute", top: 10, right: 10,
          display: "flex", alignItems: "center", gap: 5,
          background: "rgba(0,0,0,0.6)", backdropFilter: "blur(6px)",
          padding: "4px 10px", borderRadius: 6,
          fontSize: 11, fontWeight: 600, fontFamily: MM.font,
          color: divergenceColor(m.demo_score),
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: "50%",
            background: divergenceColor(m.demo_score),
          }} />
          {divergenceLabel(m.demo_score)}
        </div>
        {/* Volume badge */}
        <div style={{
          position: "absolute", top: 10, left: 10,
          background: "rgba(0,0,0,0.6)", backdropFilter: "blur(6px)",
          padding: "4px 10px", borderRadius: 6,
          fontSize: 11, color: MM.textSub, fontFamily: MM.font,
        }}>
          {vol} Vol
        </div>
        {/* Question overlay */}
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0,
          padding: "12px 14px",
        }}>
          <p style={{
            fontSize: 14, fontWeight: 600, color: "#fff",
            margin: 0, lineHeight: 1.45,
            textShadow: "0 1px 4px rgba(0,0,0,0.5)",
          }}>
            {m.question}
          </p>
        </div>
      </div>
      {/* Footer */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "10px 14px", borderTop: `1px solid ${MM.border}`,
      }}>
        <div style={{ display: "flex", gap: 8 }}>
          <span style={{
            padding: "4px 10px", borderRadius: 5, fontSize: 12, fontWeight: 600,
            background: MM.greenDim, color: MM.green, fontFamily: MM.font,
          }}>
            Yes {pct(yesP)}
          </span>
          <span style={{
            padding: "4px 10px", borderRadius: 5, fontSize: 12, fontWeight: 600,
            background: MM.redDim, color: MM.red, fontFamily: MM.font,
          }}>
            No {pct(noP)}
          </span>
        </div>
        {m.featured && (
          <span style={{
            fontSize: 10, color: MM.amber, border: `1px solid rgba(251,191,36,0.3)`,
            padding: "2px 8px", borderRadius: 4, letterSpacing: "0.05em",
          }}>
            FEATURED
          </span>
        )}
      </div>
    </div>
  );
}

// ── Market Card ─────────────────────────────────────────────────────────────

function MarketCard({ m }: { m: DbMarket }) {
  const router = useRouter();
  const [hovered, setHovered] = useState(false);

  const yesP = m.last_trade_price ?? 0;
  const noP = 1 - yesP;
  const vol = compactVol(m.volume_num ?? m.volume ?? null);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={m.question}
      onClick={() => router.push(`/markets/${m.polymarket_id}`)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") router.push(`/markets/${m.polymarket_id}`); }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex", flexDirection: "column",
        borderRadius: 10, overflow: "hidden",
        border: `1px solid ${hovered ? MM.borderHover : MM.border}`,
        background: MM.surface,
        cursor: "pointer",
        transition: "border-color 0.2s, transform 0.15s",
        transform: hovered ? "translateY(-2px)" : "none",
      }}
    >
      {/* Image */}
      <div style={{
        height: 120, position: "relative", overflow: "hidden",
        background: "#111114",
      }}>
        {m.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={m.image_url} alt=""
            style={{ width: "100%", height: "100%", objectFit: "cover", opacity: hovered ? 1 : 0.85, transition: "opacity 0.2s" }}
          />
        ) : null}
        {/* Signal dot */}
        <div style={{
          position: "absolute", top: 8, right: 8,
          display: "flex", alignItems: "center", gap: 4,
          background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)",
          padding: "3px 8px", borderRadius: 5,
          fontSize: 10, fontWeight: 600, fontFamily: MM.font,
          color: divergenceColor(m.demo_score),
        }}>
          <span style={{
            width: 5, height: 5, borderRadius: "50%",
            background: divergenceColor(m.demo_score),
          }} />
          {divergenceLabel(m.demo_score)}
        </div>
      </div>

      {/* Body */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: "12px 14px", gap: 10 }}>
        <p style={{
          fontSize: 13, fontWeight: 500, color: MM.text,
          margin: 0, lineHeight: 1.5,
          display: "-webkit-box", WebkitLineClamp: 3,
          WebkitBoxOrient: "vertical", overflow: "hidden",
        }}>
          {m.question}
        </p>

        {/* Yes / No */}
        <div style={{ display: "flex", gap: 6 }}>
          <div style={{
            flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
            padding: "6px 0", borderRadius: 5,
            background: MM.greenDim, fontSize: 12, fontWeight: 600,
            color: MM.green, fontFamily: MM.font,
          }}>
            Yes {pct(yesP)}
          </div>
          <div style={{
            flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
            padding: "6px 0", borderRadius: 5,
            background: MM.redDim, fontSize: 12, fontWeight: 600,
            color: MM.red, fontFamily: MM.font,
          }}>
            No {pct(noP)}
          </div>
        </div>

        {/* Bottom row */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          marginTop: "auto", paddingTop: 4,
          borderTop: `1px solid ${MM.border}`,
          fontSize: 11, color: MM.dim,
        }}>
          <span>{vol} Vol</span>
          {m.featured && (
            <span style={{ color: MM.amber, fontSize: 10 }}>FEATURED</span>
          )}
        </div>
      </div>
    </div>
  );
}
