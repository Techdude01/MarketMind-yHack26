"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:5001";

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

type SearchMarket = {
  polymarket_id: number;
  slug: string | null;
  question: string;
  description: string | null;
  image_url: string | null;
  end_date: string | null;
  active: boolean | null;
  closed: boolean | null;
  last_trade_price: number | null;
  volume: number | null;
  volume_num: number | null;
  liquidity: number | null;
  outcomes: string[] | null;
  outcome_prices: string[] | null;
};

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

// ── Agentic pipeline stage definitions ──────────────────────────────────────

const AGENT_STAGES = [
  { label: "Ingesting market from Polymarket", icon: "download", delayMs: 0 },
  { label: "K2 Think V2: initial reasoning", icon: "brain", delayMs: 5000 },
  { label: "Tavily: searching news sources", icon: "search", delayMs: 14000 },
  { label: "K2 Think V2: analyzing results", icon: "brain", delayMs: 25000 },
  { label: "Generating trade thesis", icon: "doc", delayMs: 38000 },
  { label: "Custom transformer sentiment analysis model", icon: "chart", delayMs: 48000 },
] as const;

// ── Main panel ──────────────────────────────────────────────────────────────

export function AgentSearchPanel() {
  const [query, setQuery] = useState("");
  const [markets, setMarkets] = useState<SearchMarket[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);
  const [analyzingMarket, setAnalyzingMarket] = useState<SearchMarket | null>(null);
  const [analysisDone, setAnalysisDone] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const router = useRouter();

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setMarkets([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    setError("");
    setSearched(true);
    try {
      const res = await fetch(
        `${API_BASE}/markets/search?q=${encodeURIComponent(q.trim())}&limit=30`
      );
      const body: unknown = await res.json().catch(() => ({}));
      if (!res.ok) {
        const errMsg =
          typeof body === "object" &&
          body !== null &&
          "error" in body &&
          typeof (body as { error: unknown }).error === "string"
            ? (body as { error: string }).error
            : `HTTP ${res.status}`;
        setError(errMsg);
        setMarkets([]);
        return;
      }
      const list =
        typeof body === "object" &&
        body !== null &&
        "markets" in body &&
        Array.isArray((body as { markets: unknown }).markets)
          ? ((body as { markets: SearchMarket[] }).markets)
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
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) {
      setMarkets([]);
      setSearched(false);
      return;
    }
    debounceRef.current = setTimeout(() => {
      void doSearch(query);
    }, 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, doSearch]);

  const handleAnalyze = async (market: SearchMarket) => {
    setAnalyzingMarket(market);
    setAnalysisDone(false);
    setError("");
    try {
      const res = await fetch(
        `${API_BASE}/analyze/search/${market.polymarket_id}`,
        { method: "POST" }
      );
      if (!res.ok) {
        const body: unknown = await res.json().catch(() => ({}));
        const errMsg =
          typeof body === "object" &&
          body !== null &&
          "error" in body &&
          typeof (body as { error: unknown }).error === "string"
            ? (body as { error: string }).error
            : `Analysis failed (HTTP ${res.status})`;
        setError(errMsg);
        setAnalyzingMarket(null);
        return;
      }
      setAnalysisDone(true);
      await new Promise((r) => setTimeout(r, 600));
      router.push(`/markets/${market.polymarket_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setAnalyzingMarket(null);
    }
  };

  return (
    <div
      style={{
        maxWidth: 1320,
        margin: "0 auto",
        padding: "28px 24px 64px",
        fontFamily: MM.font,
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1
          style={{
            fontSize: 24,
            fontWeight: 700,
            color: MM.text,
            margin: 0,
            letterSpacing: "-0.02em",
          }}
        >
          Agent
        </h1>
        <p style={{ marginTop: 4, fontSize: 13, color: MM.dim }}>
          Search any Polymarket trade and run AI analysis
        </p>
      </div>

      {/* Search bar */}
      <div
        style={{
          marginBottom: 28,
          paddingBottom: 16,
          borderBottom: `1px solid ${MM.border}`,
        }}
      >
        <div style={{ position: "relative", maxWidth: 600 }}>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke={MM.dim}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              position: "absolute",
              left: 12,
              top: "50%",
              transform: "translateY(-50%)",
            }}
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Search Polymarket..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              width: "100%",
              padding: "12px 12px 12px 36px",
              background: MM.surface,
              border: `1px solid ${MM.border}`,
              color: MM.text,
              fontSize: 14,
              fontFamily: MM.font,
              borderRadius: 8,
              outline: "none",
            }}
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div
          style={{
            marginBottom: 20,
            border: `1px solid ${MM.red}`,
            background: "rgba(248,113,113,0.06)",
            padding: "10px 14px",
            fontSize: 12,
            color: MM.red,
            borderRadius: 8,
          }}
        >
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div
          style={{
            fontSize: 13,
            color: MM.dim,
            padding: "40px 0",
            textAlign: "center",
          }}
        >
          Searching Polymarket...
        </div>
      )}

      {/* Agentic workflow overlay */}
      {analyzingMarket !== null && (
        <AgentWorkflowOverlay
          market={analyzingMarket}
          done={analysisDone}
        />
      )}

      {/* Empty state */}
      {!loading && searched && markets.length === 0 && !error && (
        <div
          style={{
            fontSize: 13,
            color: MM.ghost,
            padding: "40px 0",
            textAlign: "center",
          }}
        >
          No markets found for &quot;{query}&quot;
        </div>
      )}

      {/* Prompt */}
      {!searched && !loading && (
        <div
          style={{
            padding: "60px 0",
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 16, opacity: 0.3 }}>
            &#8981;
          </div>
          <div style={{ color: MM.dim, fontSize: 13 }}>
            Search for any prediction market on Polymarket
          </div>
          <div style={{ color: MM.ghost, fontSize: 12, marginTop: 6 }}>
            e.g. &quot;election&quot;, &quot;bitcoin&quot;, &quot;AI&quot;,
            &quot;fed rate&quot;
          </div>
        </div>
      )}

      {/* Results grid */}
      {markets.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 12,
              color: MM.dim,
              marginBottom: 12,
              letterSpacing: "0.06em",
            }}
          >
            {markets.length} RESULT{markets.length !== 1 ? "S" : ""}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 14,
            }}
          >
            {markets.map((m) => (
              <AgentMarketCard
                key={m.polymarket_id}
                m={m}
                analyzing={analyzingMarket?.polymarket_id === m.polymarket_id}
                onAnalyze={() => void handleAnalyze(m)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Agentic workflow overlay ────────────────────────────────────────────────

function AgentWorkflowOverlay({
  market,
  done,
}: {
  market: SearchMarket;
  done: boolean;
}) {
  const [activeStep, setActiveStep] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());

  useEffect(() => {
    if (done) {
      setActiveStep(AGENT_STAGES.length);
      return;
    }

    const timers = AGENT_STAGES.map((stage, i) =>
      setTimeout(() => setActiveStep(i + 1), stage.delayMs)
    );

    const tick = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);

    return () => {
      timers.forEach(clearTimeout);
      clearInterval(tick);
    };
  }, [done]);

  const allDone = done || activeStep >= AGENT_STAGES.length;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(12,12,14,0.92)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: MM.font,
      }}
    >
      <style>{`
        @keyframes agent-spin { to { transform: rotate(360deg); } }
        @keyframes agent-pulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }
        @keyframes agent-glow { 0%,100% { box-shadow: 0 0 8px rgba(74,222,128,0.15); } 50% { box-shadow: 0 0 24px rgba(74,222,128,0.35); } }
        @keyframes agent-fade-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes agent-dots { 0% { content: ''; } 25% { content: '.'; } 50% { content: '..'; } 75% { content: '...'; } }
        @keyframes agent-node-pulse { 0%,100% { transform: scale(1); opacity: 0.6; } 50% { transform: scale(1.3); opacity: 1; } }
      `}</style>

      <div
        style={{
          width: "100%",
          maxWidth: 520,
          padding: "28px 28px 24px",
          border: `1px solid rgba(74,222,128,0.2)`,
          borderRadius: 12,
          background: "linear-gradient(180deg, rgba(22,22,26,0.98) 0%, rgba(12,12,14,0.98) 100%)",
          animation: "agent-glow 3s ease-in-out infinite",
        }}
      >
        {/* Header with brain icon */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              border: `1px solid rgba(74,222,128,0.3)`,
              background: "rgba(74,222,128,0.06)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              animation: allDone ? "none" : "agent-pulse 2s ease-in-out infinite",
            }}
          >
            <svg
              width="18" height="18" viewBox="0 0 24 24" fill="none"
              stroke={MM.green} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
            >
              <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z" />
              <line x1="9" y1="21" x2="15" y2="21" />
              <line x1="10" y1="17" x2="10" y2="21" />
              <line x1="14" y1="17" x2="14" y2="21" />
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: MM.green, letterSpacing: "0.03em" }}>
              {allDone ? "ANALYSIS COMPLETE" : "AGENT RUNNING"}
            </div>
            <div style={{ fontSize: 11, color: MM.dim, marginTop: 2 }}>
              K2 Think V2 ReAct Pipeline
            </div>
          </div>
          {!allDone && (
            <div
              style={{
                marginLeft: "auto",
                width: 18, height: 18,
                border: `2px solid ${MM.ghost}`,
                borderTopColor: MM.green,
                borderRadius: "50%",
                animation: "agent-spin 0.8s linear infinite",
              }}
            />
          )}
        </div>

        {/* Market question context */}
        <div
          style={{
            padding: "10px 12px",
            background: "rgba(255,255,255,0.03)",
            border: `1px solid ${MM.border}`,
            borderRadius: 6,
            marginBottom: 20,
            fontSize: 12,
            color: MM.textSub,
            lineHeight: 1.5,
          }}
        >
          <span style={{ color: MM.dim, fontSize: 10, letterSpacing: "0.06em" }}>MARKET </span>
          {market.question}
        </div>

        {/* Pipeline steps */}
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {AGENT_STAGES.map((stage, i) => {
            const completed = i < activeStep;
            const active = i === activeStep - 1 && !allDone;
            const pending = i >= activeStep;
            const isLast = i === AGENT_STAGES.length - 1;

            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  animation: completed || active ? "agent-fade-in 0.3s ease-out" : "none",
                }}
              >
                {/* Vertical connector line + node */}
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 20 }}>
                  <div
                    style={{
                      width: completed || (allDone && i < AGENT_STAGES.length) ? 20 : active ? 16 : 10,
                      height: completed || (allDone && i < AGENT_STAGES.length) ? 20 : active ? 16 : 10,
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      marginTop: 2,
                      background: completed || (allDone && i < AGENT_STAGES.length)
                        ? "rgba(74,222,128,0.15)"
                        : active
                          ? "rgba(74,222,128,0.1)"
                          : "transparent",
                      border: completed || (allDone && i < AGENT_STAGES.length)
                        ? `1.5px solid ${MM.green}`
                        : active
                          ? `1.5px solid ${MM.green}`
                          : `1.5px solid ${MM.ghost}`,
                      animation: active ? "agent-node-pulse 1.5s ease-in-out infinite" : "none",
                      transition: "all 0.3s ease",
                    }}
                  >
                    {(completed || (allDone && i < AGENT_STAGES.length)) && (
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke={MM.green} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </div>
                  {!isLast && (
                    <div
                      style={{
                        width: 1.5,
                        height: 20,
                        background: completed
                          ? "rgba(74,222,128,0.3)"
                          : `rgba(255,255,255,0.06)`,
                        transition: "background 0.3s",
                      }}
                    />
                  )}
                </div>

                {/* Label */}
                <div style={{ paddingBottom: isLast ? 0 : 10, minHeight: isLast ? "auto" : 40, display: "flex", alignItems: "center" }}>
                  <StageIcon type={stage.icon} color={completed || (allDone && i < AGENT_STAGES.length) ? MM.green : active ? MM.green : MM.ghost} />
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: active ? 500 : 400,
                      color: completed || (allDone && i < AGENT_STAGES.length)
                        ? MM.green
                        : active
                          ? MM.text
                          : pending
                            ? MM.ghost
                            : MM.dim,
                      marginLeft: 8,
                      transition: "color 0.3s",
                    }}
                  >
                    {stage.label}
                    {active && <AnimatedEllipsis />}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer with elapsed time */}
        <div
          style={{
            marginTop: 20,
            paddingTop: 14,
            borderTop: `1px solid ${MM.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: 11,
            color: MM.dim,
          }}
        >
          <span>
            {allDone
              ? "Redirecting to analysis view..."
              : "This may take 50\u201360 seconds"}
          </span>
          <span style={{ fontVariantNumeric: "tabular-nums", color: allDone ? MM.green : MM.dim }}>
            {elapsed}s
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Animated ellipsis ───────────────────────────────────────────────────────

function AnimatedEllipsis() {
  const [dots, setDots] = useState("");

  useEffect(() => {
    const iv = setInterval(() => {
      setDots((d) => (d.length >= 3 ? "" : d + "."));
    }, 400);
    return () => clearInterval(iv);
  }, []);

  return (
    <span style={{ color: MM.dim, width: 18, display: "inline-block" }}>
      {dots}
    </span>
  );
}

// ── Stage icons ─────────────────────────────────────────────────────────────

function StageIcon({ type, color }: { type: string; color: string }) {
  const props = {
    width: 14,
    height: 14,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: color,
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  switch (type) {
    case "download":
      return (
        <svg {...props}>
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
      );
    case "brain":
      return (
        <svg {...props}>
          <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z" />
          <line x1="9" y1="21" x2="15" y2="21" />
        </svg>
      );
    case "search":
      return (
        <svg {...props}>
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      );
    case "doc":
      return (
        <svg {...props}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
      );
    case "chart":
      return (
        <svg {...props}>
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
      );
    default:
      return null;
  }
}

// ── Market card ─────────────────────────────────────────────────────────────

function AgentMarketCard({
  m,
  analyzing,
  onAnalyze,
}: {
  m: SearchMarket;
  analyzing: boolean;
  onAnalyze: () => void;
}) {
  const [hovered, setHovered] = useState(false);

  const yesP = m.last_trade_price ?? 0;
  const noP = 1 - yesP;
  const vol = compactVol(m.volume_num ?? m.volume ?? null);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        flexDirection: "column",
        borderRadius: 10,
        overflow: "hidden",
        border: `1px solid ${hovered ? MM.borderHover : MM.border}`,
        background: MM.surface,
        transition: "border-color 0.2s, transform 0.15s",
        transform: hovered ? "translateY(-2px)" : "none",
      }}
    >
      {/* Image */}
      <div
        style={{
          height: 120,
          position: "relative",
          overflow: "hidden",
          background: "#111114",
        }}
      >
        {m.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={m.image_url}
            alt=""
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              opacity: hovered ? 1 : 0.85,
              transition: "opacity 0.2s",
            }}
          />
        ) : null}
        {/* Volume badge */}
        <div
          style={{
            position: "absolute",
            top: 8,
            right: 8,
            background: "rgba(0,0,0,0.55)",
            backdropFilter: "blur(4px)",
            padding: "3px 8px",
            borderRadius: 5,
            fontSize: 10,
            fontWeight: 600,
            fontFamily: MM.font,
            color: MM.textSub,
          }}
        >
          {vol} Vol
        </div>
      </div>

      {/* Body */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          padding: "12px 14px",
          gap: 10,
        }}
      >
        <p
          style={{
            fontSize: 13,
            fontWeight: 500,
            color: MM.text,
            margin: 0,
            lineHeight: 1.5,
            display: "-webkit-box",
            WebkitLineClamp: 3,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {m.question}
        </p>

        {/* Yes / No */}
        <div style={{ display: "flex", gap: 6 }}>
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "6px 0",
              borderRadius: 5,
              background: MM.greenDim,
              fontSize: 12,
              fontWeight: 600,
              color: MM.green,
              fontFamily: MM.font,
            }}
          >
            Yes {pct(yesP)}
          </div>
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "6px 0",
              borderRadius: 5,
              background: MM.redDim,
              fontSize: 12,
              fontWeight: 600,
              color: MM.red,
              fontFamily: MM.font,
            }}
          >
            No {pct(noP)}
          </div>
        </div>

        {/* Analyze button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onAnalyze();
          }}
          disabled={analyzing}
          style={{
            marginTop: "auto",
            padding: "8px 0",
            borderRadius: 6,
            border: `1px solid ${analyzing ? MM.ghost : "rgba(74,222,128,0.45)"}`,
            background: analyzing
              ? "transparent"
              : "rgba(74,222,128,0.08)",
            color: analyzing ? MM.dim : MM.green,
            fontSize: 12,
            fontWeight: 600,
            fontFamily: MM.font,
            cursor: analyzing ? "wait" : "pointer",
            transition: "all 0.15s",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 6,
          }}
        >
          {analyzing ? (
            <>
              <span
                style={{
                  width: 12,
                  height: 12,
                  border: `1.5px solid ${MM.ghost}`,
                  borderTopColor: MM.dim,
                  borderRadius: "50%",
                  animation: "agent-spin 0.8s linear infinite",
                  display: "inline-block",
                }}
              />
              Analyzing...
            </>
          ) : (
            <>
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
              Analyze
            </>
          )}
        </button>
      </div>
    </div>
  );
}
