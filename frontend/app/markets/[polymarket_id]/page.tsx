"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// ── Design tokens ─────────────────────────────────────────────────────────────
const MM = {
  bg: "#0C0C0E",
  surface: "#16161A",
  surface2: "#1E1E24",
  border: "rgba(255,255,255,0.12)",
  borderBright: "rgba(255,255,255,0.28)",
  text: "#F4F4F5",       // bumped from E4E4E7
  textSub: "#D4D4D8",    // new — subtext, was dim
  dim: "#A1A1AA",        // bumped from 71717A
  ghost: "#71717A",      // bumped from 3F3F46
  green: "#4ADE80",
  red: "#F87171",
  yellow: "#FCD34D",
  font: "'JetBrains Mono', monospace",
} as const;

const BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:5001"
).replace(/\/$/, "");

// ── Types ──────────────────────────────────────────────────────────────────────
interface MarketDetail {
  polymarket_id: number;
  slug: string | null;
  question: string;
  description: string | null;
  resolution_source: string | null;
  image_url: string | null;
  icon_url: string | null;
  start_date: string | null;
  end_date: string | null;
  updated_at_api: string | null;
  closed_time: string | null;
  active: boolean | null;
  closed: boolean | null;
  archived: boolean | null;
  featured: boolean | null;
  new: boolean | null;
  restricted: boolean | null;
  last_trade_price: number | null;
  best_bid: number | null;
  best_ask: number | null;
  spread: number | null;
  volume: number | null;
  volume_num: number | null;
  volume_1wk: number | null;
  volume_1mo: number | null;
  volume_1yr: number | null;
  liquidity: number | null;
  outcomes: string[] | null;
  outcome_prices: string[] | null;
  clob_token_ids: string[] | null;
  first_seen_at: string | null;
  last_ingested_at: string | null;
}

interface ThesisRow {
  thesis_text: string;
  model: string;
  created_at: string;
}

interface NewsItem {
  title?: string;
  url?: string;
  score?: number;
  published_date?: string;
  content?: string;
}

interface OrderBookLevel {
  price: string;
  size: string;
}

interface OrderBook {
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  token_id?: string;
}

interface MarketSignal {
  impliedProb: number | null;
  spreadPct: number | null;
  liquidityDepth: number | null;
}

// ── Formatters ────────────────────────────────────────────────────────────────
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
  return `${(n * 100).toFixed(1)}¢`;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatSpread(bid: number | null, ask: number | null): string {
  if (bid == null || ask == null) return "—";
  return `${((ask - bid) * 100).toFixed(2)}¢`;
}

function computeSignal(
  market: MarketDetail,
  books: (OrderBook | null)[],
): MarketSignal {
  const bid = market.best_bid;
  const ask = market.best_ask;

  const impliedProb =
    bid != null && ask != null ? (bid + ask) / 2 : market.last_trade_price;

  const spreadPct =
    bid != null && ask != null && bid > 0
      ? ((ask - bid) / bid) * 100
      : null;

  const yesBook = books[0];
  const liquidityDepth =
    yesBook && yesBook.bids.length > 0
      ? yesBook.bids
          .slice(0, 5)
          .reduce((sum, lvl) => sum + parseFloat(lvl.size || "0"), 0)
      : null;

  return { impliedProb, spreadPct, liquidityDepth };
}

function sourceDomain(url: string | undefined): string {
  if (!url) return "";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

function scoreColor(score: number | undefined): string {
  if (score == null) return MM.ghost;
  if (score >= 0.7) return MM.green;
  if (score >= 0.4) return MM.yellow;
  return MM.dim;
}

// ── Sub-components ────────────────────────────────────────────────────────────
function SectionHeader({ label }: { label: string }) {
  return (
    <div
      style={{
        fontSize: 10,
        letterSpacing: "0.12em",
        color: MM.ghost,
        marginBottom: 12,
        paddingBottom: 8,
        borderBottom: `1px solid ${MM.border}`,
      }}
    >
      // _{label}
    </div>
  );
}

function StatusBadge({
  label,
  color,
  borderColor,
}: {
  label: string;
  color: string;
  borderColor: string;
}) {
  return (
    <span
      style={{
        fontSize: 10,
        letterSpacing: "0.1em",
        color,
        border: `1px solid ${borderColor}`,
        padding: "2px 8px",
        fontFamily: MM.font,
      }}
    >
      {label}
    </span>
  );
}

function StatCell({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        background: MM.surface2,
        border: `1px solid ${MM.border}`,
        padding: "12px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <div style={{ fontSize: 10, color: MM.dim, letterSpacing: "0.08em" }}>
        {label}
      </div>
      <div style={{ fontSize: 16, fontWeight: 600, color: MM.text }}>
        {value}
      </div>
    </div>
  );
}

function SignalCell({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 160,
        background: MM.surface2,
        border: `1px solid ${MM.border}`,
        borderTop: `2px solid ${accent ?? MM.border}`,
        padding: "16px 20px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <div style={{ fontSize: 10, color: MM.dim, letterSpacing: "0.1em" }}>
        {label}
      </div>
      <div
        style={{
          fontSize: 24,
          fontWeight: 700,
          color: accent ?? MM.text,
          letterSpacing: "-0.02em",
        }}
      >
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 10, color: MM.ghost }}>{sub}</div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function MarketDetailPage() {
  const params = useParams();
  const polymarket_id = Number(params["polymarket_id"]);

  const [market, setMarket] = useState<MarketDetail | null>(null);
  const [thesis, setThesis] = useState<ThesisRow | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [orderBooks, setOrderBooks] = useState<(OrderBook | null)[]>([]);
  const [loadingMarket, setLoadingMarket] = useState(true);
  const [loadingThesis, setLoadingThesis] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string>("");
  const [error, setError] = useState<string>("");

  const fetchMarket = useCallback(async () => {
    setLoadingMarket(true);
    try {
      const res = await fetch(`${BASE_URL}/markets/${polymarket_id}`);
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { error?: string };
        setError(body.error ?? `HTTP ${res.status}`);
        return;
      }
      setMarket((await res.json()) as MarketDetail);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingMarket(false);
    }
  }, [polymarket_id]);

  const fetchThesis = useCallback(async () => {
    setLoadingThesis(true);
    try {
      const res = await fetch(`${BASE_URL}/thesis/${polymarket_id}`);
      if (!res.ok) return;
      const data = (await res.json()) as {
        thesis: ThesisRow | null;
        news: NewsItem[];
      };
      setThesis(data.thesis);
      setNews(data.news);
    } catch {
      // non-critical
    } finally {
      setLoadingThesis(false);
    }
  }, [polymarket_id]);

  const runAnalysis = useCallback(async () => {
    setAnalyzing(true);
    setAnalyzeError("");
    try {
      const res = await fetch(
        `${BASE_URL}/ingest/research/${polymarket_id}`,
        { method: "POST" },
      );
      const data = (await res.json().catch(() => ({}))) as {
        thesis?: ThesisRow | null;
        news?: NewsItem[];
        error?: string;
      };
      if (!res.ok) {
        setAnalyzeError(data.error ?? `HTTP ${res.status}`);
        return;
      }
      if (data.thesis) setThesis(data.thesis);
      if (data.news) setNews(data.news);
      setAnalyzed(true);
    } catch (e) {
      setAnalyzeError(e instanceof Error ? e.message : String(e));
    } finally {
      setAnalyzing(false);
    }
  }, [polymarket_id]);

  const fetchOrderBooks = useCallback(async (tokenIds: string[]) => {
    if (tokenIds.length === 0) return;
    try {
      const results = await Promise.all(
        tokenIds.map(async (id) => {
          const res = await fetch(`${BASE_URL}/clob/markets/orderbook/${id}`);
          if (!res.ok) return null;
          return (await res.json()) as OrderBook;
        }),
      );
      setOrderBooks(results);
    } catch {
      setOrderBooks([]);
    }
  }, []);

  useEffect(() => {
    void fetchMarket();
    void fetchThesis();
  }, [fetchMarket, fetchThesis]);

  useEffect(() => {
    if (market?.clob_token_ids && market.clob_token_ids.length > 0) {
      void fetchOrderBooks(market.clob_token_ids);
    }
  }, [market, fetchOrderBooks]);

  if (loadingMarket) {
    return (
      <div
        style={{
          background: MM.bg,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: MM.font,
          color: MM.dim,
          fontSize: 12,
        }}
      >
        fetching market...
      </div>
    );
  }

  if (error || !market) {
    return (
      <div
        style={{
          background: MM.bg,
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: MM.font,
          gap: 16,
        }}
      >
        <div
          style={{
            color: MM.red,
            fontSize: 12,
            border: `1px solid ${MM.red}`,
            padding: "10px 20px",
          }}
        >
          {error || "market not found"}
        </div>
        <Link href="/markets" style={{ color: MM.dim, fontSize: 11 }}>
          ← back to markets
        </Link>
      </div>
    );
  }

  const outcomes = market.outcomes ?? [];
  const outcomePrices = market.outcome_prices ?? [];
  const chartData = outcomes.map((name, i) => ({
    name,
    price: parseFloat(outcomePrices[i] ?? "0"),
  }));
  const signal = computeSignal(market, orderBooks);

  // Thesis staleness: flag if > 48h old
  const thesisAgeHours = thesis
    ? (Date.now() - new Date(thesis.created_at).getTime()) / 3_600_000
    : null;
  const thesisStale = thesisAgeHours != null && thesisAgeHours > 48;

  return (
    <div
      style={{
        background: MM.bg,
        minHeight: "100vh",
        color: MM.text,
        fontFamily: MM.font,
      }}
    >
      {/* ── Back nav ── */}
      <div
        style={{
          borderBottom: `1px solid ${MM.border}`,
          padding: "12px 32px",
          display: "flex",
          alignItems: "center",
          gap: 16,
        }}
      >
        <Link
          href="/markets"
          style={{ color: MM.dim, fontSize: 11, textDecoration: "none" }}
          onMouseEnter={(e) => (e.currentTarget.style.color = MM.green)}
          onMouseLeave={(e) => (e.currentTarget.style.color = MM.dim)}
        >
          ← /markets
        </Link>
        <span style={{ color: MM.ghost, fontSize: 11 }}>/ {polymarket_id}</span>
      </div>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>
        {/* ── 1. Hero ── */}
        <section style={{ marginBottom: 40 }}>
          <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
            {market.icon_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={market.icon_url}
                alt=""
                style={{ width: 48, height: 48, objectFit: "contain", flexShrink: 0 }}
              />
            )}
            <div style={{ flex: 1 }}>
              <div
                style={{
                  fontSize: 10,
                  letterSpacing: "0.12em",
                  color: MM.ghost,
                  marginBottom: 8,
                }}
              >
                // _market_detail
              </div>
              <h1
                style={{
                  fontSize: "clamp(18px, 2.5vw, 26px)",
                  fontWeight: 700,
                  margin: "0 0 12px",
                  lineHeight: 1.4,
                  letterSpacing: "-0.02em",
                }}
              >
                {market.question}
              </h1>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
                {market.active && <StatusBadge label="ACTIVE" color={MM.green} borderColor={MM.green} />}
                {market.closed && <StatusBadge label="CLOSED" color={MM.ghost} borderColor={MM.border} />}
                {market.featured && <StatusBadge label="FEATURED" color={MM.yellow} borderColor="rgba(252,211,77,0.4)" />}
                {market.archived && <StatusBadge label="ARCHIVED" color={MM.dim} borderColor={MM.border} />}
                {market.new && <StatusBadge label="NEW" color="#60A5FA" borderColor="rgba(96,165,250,0.4)" />}
                {market.restricted && <StatusBadge label="RESTRICTED" color={MM.red} borderColor="rgba(248,113,113,0.4)" />}
              </div>
              {market.description && (
                <p style={{ fontSize: 12, color: MM.textSub, lineHeight: 1.7, margin: "0 0 14px", maxWidth: 720 }}>
                  {market.description}
                </p>
              )}
              {market.slug && (
                // URL ANALYSIS (do not fix):
                // Current formula: https://polymarket.com/event/{slug}
                // Why it's wrong: The Gamma API `slug` field is the *market-level* slug
                // (e.g. "will-x-happen-1234"), not the *event/group* slug that Polymarket
                // uses in its UI URLs. Polymarket's web app routes to events (grouped markets)
                // via a different slug stored on the parent event object, not on individual
                // market rows. The Gamma API does not expose the parent event slug directly —
                // it would need to be fetched from the CLOB API's market detail
                // (`/markets/{condition_id}`) and extracted from `market_slug` or the
                // `events[].slug` field. Until we fetch and store that parent event slug,
                // this link will land on a 404 or the wrong event.
                // Correct formula: https://polymarket.com/event/{event_slug}
                // where event_slug comes from the CLOB market detail response.
                <a
                  href={`https://polymarket.com/event/${market.slug}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontSize: 11,
                    color: MM.dim,
                    textDecoration: "none",
                    border: `1px solid ${MM.border}`,
                    padding: "4px 10px",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = MM.green; e.currentTarget.style.color = MM.green; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = MM.border; e.currentTarget.style.color = MM.dim; }}
                >
                  ↗ view on polymarket.com
                </a>
              )}
            </div>
          </div>
        </section>

        {/* ── 2. Key Stats ── */}
        <section style={{ marginBottom: 40 }}>
          <SectionHeader label="key_stats" />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
              gap: 2,
            }}
          >
            <StatCell label="last_trade" value={formatPrice(market.last_trade_price)} />
            <StatCell label="best_bid" value={formatPrice(market.best_bid)} />
            <StatCell label="best_ask" value={formatPrice(market.best_ask)} />
            <StatCell label="spread" value={formatSpread(market.best_bid, market.best_ask)} />
            <StatCell label="liquidity" value={formatUsd(market.liquidity)} />
            <StatCell label="vol_1wk" value={formatUsd(market.volume_1wk ?? market.volume_num)} />
            <StatCell label="vol_1mo" value={formatUsd(market.volume_1mo)} />
            <StatCell
              label="ends"
              value={market.end_date ? (formatDate(market.end_date).split(",")[0] ?? "—") : "—"}
            />
          </div>
        </section>

        {/* ── 3. Market Signal ── */}
        <section style={{ marginBottom: 40 }}>
          <SectionHeader label="market_signal" />
          <div style={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <SignalCell
              label="implied_probability"
              value={
                signal.impliedProb != null
                  ? `${(signal.impliedProb * 100).toFixed(1)}%`
                  : "—"
              }
              sub="mid-price (bid + ask) / 2"
              accent={
                signal.impliedProb != null && signal.impliedProb >= 0.5
                  ? MM.green
                  : MM.red
              }
            />
            <SignalCell
              label="spread_%"
              value={
                signal.spreadPct != null
                  ? `${signal.spreadPct.toFixed(2)}%`
                  : "—"
              }
              sub={
                signal.spreadPct != null
                  ? signal.spreadPct < 3
                    ? "tight — efficient market"
                    : signal.spreadPct < 8
                    ? "moderate spread"
                    : "wide — low liquidity"
                  : "no data"
              }
              accent={
                signal.spreadPct != null
                  ? signal.spreadPct < 3
                    ? MM.green
                    : signal.spreadPct < 8
                    ? MM.yellow
                    : MM.red
                  : MM.ghost
              }
            />
            <SignalCell
              label="bid_depth_5"
              value={
                signal.liquidityDepth != null
                  ? formatUsd(signal.liquidityDepth)
                  : "—"
              }
              sub="top 5 bid levels, YES side"
              accent={MM.text}
            />
          </div>
        </section>

        {/* ── Analyze bar ── */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 12,
            marginBottom: 40,
            padding: "14px 20px",
            background: MM.surface,
            border: `1px solid ${MM.border}`,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 11, color: MM.textSub }}>
              Run Tavily search + Gemini thesis for this market
            </span>
            {analyzeError && (
              <span style={{ fontSize: 10, color: MM.red }}>{analyzeError}</span>
            )}
          </div>
          <button
            type="button"
            disabled={analyzing || analyzed}
            onClick={() => void runAnalysis()}
            style={{
              border: analyzed ? `1px solid ${MM.ghost}` : "none",
              background: analyzed ? "transparent" : analyzing ? MM.ghost : MM.green,
              color: analyzed ? MM.ghost : MM.bg,
              padding: "8px 20px",
              fontSize: 12,
              fontFamily: MM.font,
              fontWeight: 500,
              cursor: analyzing || analyzed ? "not-allowed" : "pointer",
              borderRadius: 0,
              transition: "opacity 0.2s",
              opacity: analyzing ? 0.6 : 1,
              letterSpacing: "0.04em",
              whiteSpace: "nowrap",
            }}
            onMouseEnter={(e) => { if (!analyzing && !analyzed) e.currentTarget.style.opacity = "0.85"; }}
            onMouseLeave={(e) => { e.currentTarget.style.opacity = analyzing ? "0.6" : "1"; }}
          >
            {analyzed ? "✓ analyzed" : analyzing ? "_ analyzing..." : "> analyze_market"}
          </button>
        </div>

        {/* ── 4. AI Analysis ── */}
        <section style={{ marginBottom: 40 }}>
          <SectionHeader label="ai_analysis" />
          {loadingThesis ? (
            <div style={{ fontSize: 11, color: MM.dim }}>fetching thesis...</div>
          ) : thesis ? (
            <div
              style={{
                background: MM.surface,
                border: `1px solid ${MM.border}`,
                borderLeft: `3px solid ${MM.green}`,
                padding: "20px 24px",
              }}
            >
              {/* Thesis header */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 16,
                  flexWrap: "wrap",
                }}
              >
                <span
                  style={{
                    fontSize: 10,
                    letterSpacing: "0.08em",
                    color: MM.green,
                    border: `1px solid ${MM.green}`,
                    padding: "2px 8px",
                  }}
                >
                  {thesis.model}
                </span>
                <span style={{ fontSize: 10, color: MM.dim }}>
                  generated {formatDate(thesis.created_at)}
                </span>
                {thesisStale && (
                  <span
                    style={{
                      fontSize: 10,
                      color: MM.yellow,
                      border: `1px solid rgba(252,211,77,0.4)`,
                      padding: "2px 8px",
                    }}
                  >
                    ⚠ stale — {Math.floor(thesisAgeHours ?? 0)}h old
                  </span>
                )}
              </div>
              <div className="thesis-body">
                <ReactMarkdown>{thesis.thesis_text}</ReactMarkdown>
              </div>
              <style>{`
                .thesis-body { font-family: ${MM.font}; font-size: 12px; line-height: 1.9; color: ${MM.textSub}; }
                .thesis-body h1, .thesis-body h2, .thesis-body h3 { color: ${MM.text}; font-weight: 700; margin: 16px 0 6px; letter-spacing: -0.01em; }
                .thesis-body h1 { font-size: 15px; }
                .thesis-body h2 { font-size: 13px; border-bottom: 1px solid ${MM.border}; padding-bottom: 4px; }
                .thesis-body h3 { font-size: 12px; color: ${MM.dim}; }
                .thesis-body p { margin: 0 0 10px; }
                .thesis-body strong { color: ${MM.text}; font-weight: 600; }
                .thesis-body em { color: ${MM.dim}; }
                .thesis-body ul, .thesis-body ol { padding-left: 20px; margin: 0 0 10px; }
                .thesis-body li { margin: 4px 0; }
                .thesis-body code { background: rgba(74,222,128,0.08); color: ${MM.green}; padding: 1px 5px; font-family: ${MM.font}; font-size: 11px; }
                .thesis-body blockquote { border-left: 2px solid ${MM.ghost}; margin: 0 0 10px; padding: 4px 12px; color: ${MM.dim}; }
                .thesis-body a { color: ${MM.green}; text-decoration: none; }
                .thesis-body a:hover { text-decoration: underline; }
              `}</style>
            </div>
          ) : (
            <div
              style={{
                background: MM.surface,
                border: `1px solid ${MM.border}`,
                padding: 20,
                fontSize: 11,
                color: MM.ghost,
              }}
            >
              no_thesis — run{" "}
              <code
                style={{
                  color: MM.green,
                  background: "rgba(74,222,128,0.08)",
                  padding: "1px 5px",
                }}
              >
                POST /ingest/pipeline
              </code>{" "}
              to generate analysis.
            </div>
          )}
        </section>

        {/* ── 5. News & Research ── */}
        <section style={{ marginBottom: 40 }}>
          <SectionHeader label="news_and_research" />
          {news.length === 0 ? (
            <div
              style={{
                background: MM.surface,
                border: `1px solid ${MM.border}`,
                padding: 20,
                fontSize: 11,
                color: MM.ghost,
              }}
            >
              no_news — run{" "}
              <code
                style={{
                  color: MM.green,
                  background: "rgba(74,222,128,0.08)",
                  padding: "1px 5px",
                }}
              >
                POST /ingest/pipeline
              </code>{" "}
              to fetch Tavily results.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {news.map((item, i) => {
                const domain = sourceDomain(item.url);
                const sc = item.score;
                return (
                  <div
                    key={i}
                    style={{
                      background: MM.surface,
                      border: `1px solid ${MM.border}`,
                      borderLeft: `2px solid ${scoreColor(sc)}`,
                      padding: "14px 16px",
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                    }}
                  >
                    {/* Title row */}
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        gap: 12,
                      }}
                    >
                      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4 }}>
                        {item.url ? (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              fontSize: 12,
                              color: MM.text,
                              textDecoration: "none",
                              fontWeight: 500,
                              lineHeight: 1.5,
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.color = MM.green)}
                            onMouseLeave={(e) => (e.currentTarget.style.color = MM.text)}
                          >
                            {item.title ?? item.url}
                          </a>
                        ) : (
                          <span style={{ fontSize: 12, color: MM.text, fontWeight: 500 }}>
                            {item.title ?? "untitled"}
                          </span>
                        )}
                        {/* Source + date row */}
                        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                          {domain && (
                            <span style={{ fontSize: 10, color: MM.ghost }}>{domain}</span>
                          )}
                          {item.published_date && (
                            <span style={{ fontSize: 10, color: MM.ghost }}>
                              {item.published_date}
                            </span>
                          )}
                        </div>
                      </div>
                      {/* Score chip */}
                      {sc != null && (
                        <span
                          style={{
                            fontSize: 10,
                            color: scoreColor(sc),
                            border: `1px solid ${scoreColor(sc)}`,
                            padding: "2px 6px",
                            flexShrink: 0,
                            opacity: 0.8,
                          }}
                        >
                          {sc.toFixed(2)}
                        </span>
                      )}
                    </div>
                    {/* Content preview */}
                    {item.content && (
                      <p
                        style={{
                          fontSize: 11,
                          color: MM.dim,
                          margin: 0,
                          lineHeight: 1.7,
                          overflow: "hidden",
                          display: "-webkit-box",
                          WebkitLineClamp: 3,
                          WebkitBoxOrient: "vertical",
                        }}
                      >
                        {item.content}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* ── 6. Outcomes Chart ── */}
        {chartData.length > 0 && (
          <section style={{ marginBottom: 40 }}>
            <SectionHeader label="outcomes" />
            <div
              style={{
                background: MM.surface,
                border: `1px solid ${MM.border}`,
                padding: "20px 16px",
              }}
            >
              <ResponsiveContainer width="100%" height={Math.max(60, chartData.length * 52)}>
                <BarChart
                  data={chartData}
                  layout="vertical"
                  margin={{ top: 0, right: 48, bottom: 0, left: 8 }}
                >
                  <XAxis
                    type="number"
                    domain={[0, 1]}
                    tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                    tick={{ fill: MM.ghost, fontSize: 10, fontFamily: MM.font }}
                    axisLine={{ stroke: MM.border }}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={120}
                    tick={{ fill: MM.dim, fontSize: 11, fontFamily: MM.font }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: MM.surface2,
                      border: `1px solid ${MM.border}`,
                      fontFamily: MM.font,
                      fontSize: 11,
                    }}
                    formatter={(value) => [
                      `${(Number(value) * 100).toFixed(1)}%`,
                      "implied probability",
                    ]}
                  />
                  <Bar dataKey="price" radius={0} maxBarSize={20}>
                    {chartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.price >= 0.5 ? MM.green : MM.dim}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
        )}

        {/* ── 7. Metadata Footer ── */}
        <section style={{ marginBottom: 40 }}>
          <SectionHeader label="metadata" />
          <div
            style={{
              background: MM.surface,
              border: `1px solid ${MM.border}`,
              padding: "16px 20px",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
              gap: "8px 24px",
              fontSize: 11,
            }}
          >
            {(
              [
                ["polymarket_id", String(market.polymarket_id)],
                ["slug", market.slug ?? "—"],
                [
                  "resolution_source",
                  market.resolution_source
                    ? market.resolution_source.length > 50
                      ? `${market.resolution_source.slice(0, 50)}…`
                      : market.resolution_source
                    : "—",
                ],
                ["start_date", formatDate(market.start_date)],
                ["end_date", formatDate(market.end_date)],
                ["closed_time", formatDate(market.closed_time)],
                ["updated_at_api", formatDate(market.updated_at_api)],
                ["last_ingested_at", formatDate(market.last_ingested_at)],
              ] as [string, string][]
            ).map(([key, val]) => (
              <div key={key} style={{ display: "flex", gap: 8 }}>
                <span style={{ color: MM.dim, minWidth: 130 }}>{key}</span>
                <span style={{ color: MM.textSub }}>{val}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
