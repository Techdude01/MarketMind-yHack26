"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
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

const STALE_THRESHOLD_HOURS = 72;

/** Matches backend ``k2_agent._THINK_CLOSE`` — show markdown after K2's closing think tag. */
const THINK_CLOSE_TAG = "\u003c/think\u003e";

function thesisMarkdownForDisplay(text: string | undefined | null): string {
  const s = text ?? "";
  if (s.includes(THINK_CLOSE_TAG)) {
    const parts = s.split(THINK_CLOSE_TAG);
    const tail = parts[parts.length - 1];
    return tail !== undefined ? tail.trim() : s;
  }
  return s;
}

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
  agent_probability?: number | null;
  agent_confidence?: string | null;
  agent_recommendation?: string | null;
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

interface TimelinePoint {
  timestamp: string;
  /** Unix ms for Recharts numeric X-axis (avoids duplicate categorical labels). */
  x_ms?: number;
  implied_probability: number;
  label: string;
  source: string;
}

function timelineAxisLabels(points: TimelinePoint[]): [string, string, string] {
  if (points.length === 0) {
    return ["—", "—", "—"];
  }
  if (points.length === 1) {
    const only = points[0].label;
    return [only, only, only];
  }
  const mid = points[Math.floor((points.length - 1) / 2)];
  return [points[0].label, mid.label, points[points.length - 1].label];
}

/** Y-axis domain for ``deltaPctVsStart`` (relative % vs first point in range). */
function computeDeltaPctYDomain(
  points: ReadonlyArray<{ deltaPctVsStart: number }>,
): [number, number] {
  if (points.length === 0) {
    return [-1, 1];
  }
  const vals = points.map((p) => p.deltaPctVsStart);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const span = hi - lo;
  if (span < 1e-12) {
    const c = lo;
    return [c - 0.75, c + 0.75];
  }
  const pad = Math.max(span * 0.18, 0.05);
  return [lo - pad, hi + pad];
}

interface PayoffPreview {
  entry_price: number;
  position_size: number;
  agent_confidence: number;
  expected_value: number;
  roi: number;
  breakeven: number;
  max_payout: number;
  cost: number;
  pnl_curve: Array<{ probability: number; pnl: number }>;
}

interface AnalysisPayload {
  market: MarketDetail;
  thesis: ThesisRow | null;
  news: NewsItem[];
  timeline: TimelinePoint[];
  /** ``clob_prices_history`` vs ``fallback_flat`` (DB had no token + Gamma lookup failed). */
  timeline_source?: string;
  payoff_preview: PayoffPreview;
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

function ageHoursFromIso(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return null;
  return (Date.now() - ts) / 3_600_000;
}

function freshnessTone(ageHours: number | null): {
  text: string;
  color: string;
  border: string;
} {
  if (ageHours == null) {
    return { text: "unknown", color: MM.ghost, border: MM.border };
  }
  if (ageHours >= STALE_THRESHOLD_HOURS) {
    return {
      text: `${Math.floor(ageHours)}h old`,
      color: MM.yellow,
      border: "rgba(252,211,77,0.45)",
    };
  }
  return {
    text: `${Math.max(0, Math.floor(ageHours))}h old`,
    color: MM.green,
    border: "rgba(74,222,128,0.4)",
  };
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

function CardShell({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        background: MM.surface,
        border: `1px solid ${MM.border}`,
        padding: "18px 20px",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = MM.borderBright;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = MM.border;
      }}
    >
      {children}
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
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [payoffPreview, setPayoffPreview] = useState<PayoffPreview | null>(null);
  const [orderBooks, setOrderBooks] = useState<(OrderBook | null)[]>([]);
  const [loadingMarket, setLoadingMarket] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [marketFetchedAt, setMarketFetchedAt] = useState<string | null>(null);
  const [thesisFetchedAt, setThesisFetchedAt] = useState<string | null>(null);
  const [orderBookFetchedAt, setOrderBookFetchedAt] = useState<string | null>(null);

  const fetchAnalysis = useCallback(async () => {
    setLoadingMarket(true);
    try {
      const res = await fetch(`${BASE_URL}/markets/${polymarket_id}/analysis?days=30`);
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { error?: string };
        setError(body.error ?? `HTTP ${res.status}`);
        return;
      }
      const data = (await res.json()) as AnalysisPayload;
      setMarket(data.market);
      setThesis(data.thesis);
      setNews(data.news ?? []);
      setTimeline(data.timeline ?? []);
      setPayoffPreview(data.payoff_preview ?? null);
      setMarketFetchedAt(new Date().toISOString());
      setThesisFetchedAt(new Date().toISOString());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingMarket(false);
    }
  }, [polymarket_id]);

  const runAnalysis = useCallback(async () => {
    setAnalyzing(true);
    setAnalyzeError("");
    try {
      const res = await fetch(
        `${BASE_URL}/analyze/${polymarket_id}`,
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
      if (data.thesis) {
        setThesis(data.thesis);
      }
      await fetchAnalysis();
      setAnalyzed(true);
    } catch (e) {
      setAnalyzeError(e instanceof Error ? e.message : String(e));
    } finally {
      setAnalyzing(false);
    }
  }, [fetchAnalysis, polymarket_id]);

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
      setOrderBookFetchedAt(new Date().toISOString());
    } catch {
      setOrderBooks([]);
      setOrderBookFetchedAt(null);
    }
  }, []);

  useEffect(() => {
    void fetchAnalysis();
  }, [fetchAnalysis]);

  useEffect(() => {
    if (market?.clob_token_ids && market.clob_token_ids.length > 0) {
      void fetchOrderBooks(market.clob_token_ids);
    }
  }, [market, fetchOrderBooks]);

  const timelineChartData = useMemo(() => {
    const sorted = [...timeline]
      .map((p) => ({
        ...p,
        xMs: p.x_ms ?? new Date(p.timestamp).getTime(),
      }))
      .sort((a, b) => a.xMs - b.xMs);
    const p0 = sorted[0]?.implied_probability ?? 0;
    const safeBase = p0 > 1e-15 ? p0 : 1e-15;
    return sorted.map((row) => ({
      ...row,
      deltaPctVsStart: ((row.implied_probability / safeBase) - 1) * 100,
    }));
  }, [timeline]);
  const timelineYDomain = useMemo(
    () => computeDeltaPctYDomain(timelineChartData),
    [timelineChartData],
  );
  const timelineIsFallback = timeline[0]?.source === "fallback_flat";
  const timelineProbFlat = useMemo(() => {
    const vals = timelineChartData.map((r) => r.implied_probability);
    if (vals.length < 2) {
      return true;
    }
    return Math.max(...vals) - Math.min(...vals) < 1e-12;
  }, [timelineChartData]);

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
  const chartAxisLabels = timelineAxisLabels(timeline);

  const marketDataAsOf = market.updated_at_api ?? market.last_ingested_at ?? marketFetchedAt;
  const thesisAsOf = thesis?.created_at ?? thesisFetchedAt;
  const researchAsOf = thesisFetchedAt;
  const marketAgeHours = ageHoursFromIso(marketDataAsOf);
  const thesisAgeHours = ageHoursFromIso(thesisAsOf);
  const researchAgeHours = ageHoursFromIso(researchAsOf);
  const researchStale =
    news.length > 0 && researchAgeHours != null && researchAgeHours >= STALE_THRESHOLD_HOURS;
  const marketFreshness = freshnessTone(marketAgeHours);
  const thesisFreshness = freshnessTone(thesisAgeHours);
  const researchFreshness = freshnessTone(researchAgeHours);

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
        {/* ── 1. Hero + Trust Summary ── */}
        <section style={{ marginBottom: 40 }}>
          <CardShell>
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

            <div
              style={{
                marginTop: 18,
                borderTop: `1px solid ${MM.border}`,
                paddingTop: 14,
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                gap: 2,
              }}
            >
              <StatCell label="current_price" value={formatPrice(market.last_trade_price)} />
              <StatCell
                label="bid_ask_spread"
                value={`${formatPrice(market.best_bid)} / ${formatPrice(market.best_ask)} / ${formatSpread(market.best_bid, market.best_ask)}`}
              />
              <StatCell
                label="resolution_end"
                value={market.end_date ? (formatDate(market.end_date).split(",")[0] ?? "—") : "—"}
              />
              <StatCell label="volume_liquidity" value={`${formatUsd(market.volume_1wk ?? market.volume_num)} / ${formatUsd(market.liquidity)}`} />
            </div>

            <div
              style={{
                marginTop: 12,
                borderTop: `1px solid ${MM.border}`,
                paddingTop: 10,
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                gap: "8px 16px",
                fontSize: 10,
              }}
            >
              <div style={{ color: MM.dim }}>
                market_data_last_updated: <span style={{ color: marketFreshness.color }}>{formatDate(marketDataAsOf)} ({marketFreshness.text})</span>
              </div>
              <div style={{ color: MM.dim }}>
                order_book_as_of: <span style={{ color: MM.textSub }}>{formatDate(orderBookFetchedAt)}</span>
              </div>
              <div style={{ color: MM.dim }}>
                thesis_generated: <span style={{ color: thesisFreshness.color }}>{formatDate(thesisAsOf)} ({thesisFreshness.text})</span>
              </div>
              <div style={{ color: MM.dim }}>
                research_indexed: <span style={{ color: researchFreshness.color }}>{formatDate(researchAsOf)} ({researchFreshness.text})</span>
              </div>
            </div>

            <div
              style={{
                marginTop: 12,
                fontSize: 10,
                color: MM.ghost,
                border: `1px solid ${MM.border}`,
                padding: "8px 10px",
                background: "rgba(255,255,255,0.01)",
                letterSpacing: "0.03em",
              }}
            >
              data_notice: prices/odds are market-implied from Polymarket; thesis/news are model-generated research summaries and may lag new events.
            </div>
          </CardShell>
        </section>

        {/* ── 03. Terminal Analysis View ── */}
        <section style={{ marginBottom: 40 }}>
          <CardShell>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                paddingBottom: 10,
                marginBottom: 12,
                borderBottom: `1px solid ${MM.border}`,
                fontSize: 11,
                color: MM.ghost,
              }}
            >
              <span>● ● ●</span>
              <span style={{ marginLeft: 8 }}>~/marketmind/market/{market.slug ?? polymarket_id}</span>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "200px 1fr 200px",
                gap: 0,
                border: `1px solid ${MM.border}`,
                background: MM.bg,
              }}
            >
              <div style={{ borderRight: `1px solid ${MM.border}`, padding: 20 }}>
                <div style={{ fontSize: 12, color: MM.dim, marginBottom: 12 }}>IMPLIED_PROBABILITY</div>
                <div style={{ fontSize: 48, fontWeight: 700, color: MM.green, lineHeight: 1 }}>
                  {signal.impliedProb != null ? signal.impliedProb.toFixed(2) : "—"}
                </div>
              </div>

              <div style={{ borderRight: `1px solid ${MM.border}`, padding: 20 }}>
                <div style={{ fontSize: 9, color: MM.ghost, marginBottom: 6, letterSpacing: "0.06em" }}>
                  history: % change vs first point in range (CLOB often repeats the same price for many hours)
                </div>
                <ResponsiveContainer width="100%" height={170}>
                  <LineChart data={timelineChartData} margin={{ top: 10, right: 8, left: 8, bottom: 8 }}>
                    <CartesianGrid stroke={MM.border} strokeDasharray="2 2" />
                    <XAxis
                      type="number"
                      dataKey="xMs"
                      domain={["dataMin", "dataMax"]}
                      tick={{ fill: MM.ghost, fontSize: 10, fontFamily: MM.font }}
                      tickFormatter={(ms: number) =>
                        new Date(ms).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                        })
                      }
                      axisLine={{ stroke: MM.border }}
                      tickLine={false}
                    />
                    <YAxis
                      domain={timelineYDomain}
                      tick={{ fill: MM.ghost, fontSize: 10, fontFamily: MM.font }}
                      tickFormatter={(v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`}
                      axisLine={{ stroke: MM.border }}
                      tickLine={false}
                      width={44}
                    />
                    <Tooltip
                      contentStyle={{
                        background: MM.surface2,
                        border: `1px solid ${MM.border}`,
                        fontFamily: MM.font,
                        fontSize: 11,
                      }}
                      labelFormatter={(label) => {
                        const ms = typeof label === "number" ? label : Number(label);
                        if (Number.isNaN(ms)) return String(label);
                        return new Date(ms).toLocaleString(undefined, {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        });
                      }}
                      formatter={(_value, _name, item) => {
                        const pl = item?.payload as
                          | { implied_probability?: number; deltaPctVsStart?: number }
                          | undefined;
                        const p = pl?.implied_probability;
                        const d = pl?.deltaPctVsStart;
                        const line = `p=${p !== undefined ? p.toFixed(4) : "—"} · ${d !== undefined ? `${d >= 0 ? "+" : ""}${d.toFixed(2)}%` : "—"} vs start`;
                        return [line, "implied"];
                      }}
                    />
                    <Line
                      dataKey="deltaPctVsStart"
                      stroke={MM.green}
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginTop: 6,
                    fontSize: 10,
                    color: MM.ghost,
                  }}
                >
                  <span>{chartAxisLabels[0]}</span>
                  <span>{chartAxisLabels[1]}</span>
                  <span>{chartAxisLabels[2]}</span>
                </div>
                {timelineIsFallback && (
                  <div style={{ marginTop: 6, fontSize: 9, color: MM.yellow, letterSpacing: "0.04em" }}>
                    chart: placeholder (no CLOB token / empty history)
                  </div>
                )}
                {!timelineIsFallback && timelineProbFlat && (
                  <div style={{ marginTop: 6, fontSize: 9, color: MM.yellow, letterSpacing: "0.04em" }}>
                    CLOB prices did not change in this window (illiquid / stale quotes)
                  </div>
                )}
              </div>

              <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 2 }}>
                <StatCell label="CURRENT_ODDS" value={signal.impliedProb != null ? signal.impliedProb.toFixed(2) : "—"} />
                <StatCell
                  label="AGENT_PROB"
                  value={
                    thesis?.agent_probability != null
                      ? (thesis.agent_probability / 100).toFixed(2)
                      : "—"
                  }
                />
                <StatCell
                  label="EXPECTED_VALUE"
                  value={payoffPreview ? formatUsd(payoffPreview.expected_value) : "—"}
                />
              </div>
            </div>

            <div style={{ border: `1px solid ${MM.border}`, borderTop: "none", background: MM.bg }}>
              <div
                style={{
                  padding: "8px 12px",
                  borderBottom: `1px solid ${MM.border}`,
                  fontSize: 11,
                  letterSpacing: "0.12em",
                  color: MM.ghost,
                }}
              >
                [AGENT_THESIS]
              </div>
              <div style={{ padding: "14px 12px" }} className="thesis-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {thesis ? thesisMarkdownForDisplay(thesis.thesis_text) : "No thesis yet."}
                </ReactMarkdown>
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
                .thesis-body table { width: 100%; border-collapse: collapse; margin: 0 0 12px; font-size: 11px; }
                .thesis-body th, .thesis-body td { border: 1px solid ${MM.border}; padding: 8px 10px; text-align: left; vertical-align: top; }
                .thesis-body th { color: ${MM.text}; font-weight: 600; background: ${MM.surface2}; }
              `}</style>
            </div>
          </CardShell>
        </section>

        {/* ── 2. Key Stats ── */}
        <section style={{ marginBottom: 40 }}>
          <CardShell>
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
          </CardShell>
        </section>

        {/* ── 3. Market Signal ── */}
        <section style={{ marginBottom: 40 }}>
          <CardShell>
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
          </CardShell>
        </section>

        {/* ── Analyze bar ── */}
        <div style={{ marginBottom: 40 }}>
          <CardShell>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: 12,
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={{ fontSize: 11, color: MM.textSub }}>
                  Run Tavily search + K2 thesis for this market
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
          </CardShell>
        </div>

        {/* ── 4. News & Research ── */}
        <section style={{ marginBottom: 40 }}>
          <CardShell>
            <SectionHeader label="news_and_research" />
            {researchStale && (
              <div
                style={{
                  marginBottom: 10,
                  fontSize: 10,
                  color: MM.yellow,
                  border: `1px solid ${researchFreshness.border}`,
                  padding: "6px 8px",
                }}
              >
                warning: research bundle is {researchFreshness.text}; rerun analysis for newer coverage.
              </div>
            )}
            {news.length === 0 ? (
              <div
                style={{
                  border: `1px solid ${MM.border}`,
                  padding: 20,
                  fontSize: 11,
                  color: MM.ghost,
                  background: MM.surface2,
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
                  {`POST /analyze/${polymarket_id}`}
                </code>{" "}
                or use &gt; analyze_market.
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
                        background: MM.surface2,
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
                        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                          {domain && (
                            <span style={{ fontSize: 10, color: MM.ghost }}>source: {domain}</span>
                          )}
                          {item.published_date && (
                            <span style={{ fontSize: 10, color: MM.ghost }}>
                              published: {item.published_date}
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
          </CardShell>
        </section>

        {/* ── 6. Outcomes Chart ── */}
        {chartData.length > 0 && (
          <section style={{ marginBottom: 40 }}>
            <CardShell>
              <SectionHeader label="outcomes" />
              <div style={{ marginBottom: 10, fontSize: 10, color: MM.ghost }}>
                Bars show implied probability by outcome from current market prices.
              </div>
              <div
                style={{
                  background: MM.surface2,
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
            </CardShell>
          </section>
        )}

        {/* ── 7. Metadata Footer ── */}
        <section style={{ marginBottom: 40 }}>
          <CardShell>
            <SectionHeader label="metadata" />
            <div
              style={{
                background: MM.surface2,
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
          </CardShell>
        </section>
      </div>
    </div>
  );
}
