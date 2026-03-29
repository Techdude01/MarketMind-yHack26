// ── Shared design tokens ─────────────────────────────────────
export const MM = {
  bg:           "#0C0C0E",
  surface:      "#16161A",
  border:       "rgba(255,255,255,0.18)",
  borderBright: "rgba(255,255,255,0.32)",
  text:         "#E4E4E7",
  dim:          "#71717A",
  ghost:        "#3F3F46",
  green:        "#4ADE80",
  red:          "#F87171",
  font:         "'JetBrains Mono', monospace",
} as const;

// ── Data types ────────────────────────────────────────────────
export type UserInfo = {
  name: string;
  accountId: string;
  balance: number;
  accountType: "demo" | "live";
  joinedAt: string;
  totalTrades: number;
  winRate: number;    // 0.0–1.0
};

export type Trade = {
  id: string;
  market: string;
  side: "YES" | "NO";
  quantity: number;
  entryPrice: number;
  exitPrice: number | null;
  pnl: number | null;
  status: "open" | "won" | "lost";
  openedAt: string;
  closedAt: string | null;
};

export type PnLPoint = {
  date: string;
  cumulative: number;
  daily: number;
};

// ── Mock data ─────────────────────────────────────────────────
export const MOCK_USER: UserInfo = {
  name: "agent_user_01",
  accountId: "MM-0x4f3a91",
  balance: 2847.33,
  accountType: "demo",
  joinedAt: "2025-01-14",
  totalTrades: 47,
  winRate: 0.68,
};

export const MOCK_TRADES: Trade[] = [
  { id: "t01", market: "TRUMP_WINS_NH",    side: "YES", quantity: 200, entryPrice: 0.61, exitPrice: 0.73, pnl: 24.00,  status: "won",  openedAt: "2025-03-01", closedAt: "2025-03-03" },
  { id: "t02", market: "FED_CUTS_JUNE",    side: "NO",  quantity: 150, entryPrice: 0.58, exitPrice: 0.69, pnl: 16.50,  status: "won",  openedAt: "2025-03-02", closedAt: "2025-03-07" },
  { id: "t03", market: "BTC_100K_Q2",      side: "YES", quantity: 300, entryPrice: 0.44, exitPrice: 0.31, pnl: -39.00, status: "lost", openedAt: "2025-03-04", closedAt: "2025-03-10" },
  { id: "t04", market: "RECESSION_2025",   side: "NO",  quantity: 100, entryPrice: 0.52, exitPrice: 0.58, pnl: 6.00,   status: "won",  openedAt: "2025-03-06", closedAt: "2025-03-12" },
  { id: "t05", market: "AI_REGULATION_EU", side: "YES", quantity: 250, entryPrice: 0.71, exitPrice: 0.82, pnl: 27.50,  status: "won",  openedAt: "2025-03-08", closedAt: "2025-03-14" },
  { id: "t06", market: "ETH_MERGE_V2",     side: "YES", quantity: 400, entryPrice: 0.38, exitPrice: 0.20, pnl: -72.00, status: "lost", openedAt: "2025-03-09", closedAt: "2025-03-15" },
  { id: "t07", market: "CHINA_TAIWAN_2025",side: "NO",  quantity: 500, entryPrice: 0.88, exitPrice: 0.91, pnl: 15.00,  status: "won",  openedAt: "2025-03-11", closedAt: "2025-03-16" },
  { id: "t08", market: "SPOTIFY_IPO_RIVAL",side: "NO",  quantity: 200, entryPrice: 0.18, exitPrice: 0.23, pnl: -10.00, status: "lost", openedAt: "2025-03-13", closedAt: "2025-03-17" },
  { id: "t09", market: "FED_CUTS_SEPT",    side: "YES", quantity: 300, entryPrice: 0.42, exitPrice: 0.55, pnl: 39.00,  status: "won",  openedAt: "2025-03-15", closedAt: "2025-03-20" },
  { id: "t10", market: "TRUMP_WINS_NH",    side: "NO",  quantity: 100, entryPrice: 0.74, exitPrice: 0.68, pnl: 6.00,   status: "won",  openedAt: "2025-03-18", closedAt: "2025-03-22" },
  { id: "t11", market: "BTC_200K_2025",    side: "YES", quantity: 200, entryPrice: 0.22, exitPrice: null, pnl: null,   status: "open", openedAt: "2025-03-24", closedAt: null },
  { id: "t12", market: "AI_REGULATION_EU", side: "NO",  quantity: 150, entryPrice: 0.81, exitPrice: null, pnl: null,   status: "open", openedAt: "2025-03-26", closedAt: null },
];

// 30 daily PnL points
export const MOCK_PNL: PnLPoint[] = (() => {
  const days: PnLPoint[] = [];
  let cum = 0;
  const dailies = [
    4, -8, 12, 6, -4, 18, 2, -14, 24, 8,
    -6, 16, 10, -18, 22, 4, -2, 14, 8, -10,
    20, -4, 6, 12, 18, -8, 24, 6, -6, 12,
  ];
  for (let i = 0; i < 30; i++) {
    cum += dailies[i];
    const d = new Date(2025, 2, i + 1);
    days.push({
      date: d.toISOString().slice(0, 10),
      cumulative: cum,
      daily: dailies[i],
    });
  }
  return days;
})();
