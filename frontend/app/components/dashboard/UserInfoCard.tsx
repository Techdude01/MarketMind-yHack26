"use client";

import { MM, type UserInfo } from "./mock-data";

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ fontSize: 10, letterSpacing: "0.12em", color: MM.ghost, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: accent ? MM.green : MM.text, fontFamily: MM.font }}>{value}</div>
    </div>
  );
}

export default function UserInfoCard({ user }: { user: UserInfo }) {
  const winPct = Math.round(user.winRate * 100);
  const winColor = user.winRate >= 0.6 ? MM.green : user.winRate >= 0.4 ? "#FCD34D" : MM.red;

  return (
    <div
      style={{
        border: `1px solid ${MM.border}`,
        background: MM.surface,
        borderRadius: 0,
        fontFamily: MM.font,
        overflow: "hidden",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = MM.borderBright)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = MM.border)}
    >
      {/* Header bar */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "8px 16px", borderBottom: `1px solid ${MM.border}`,
        fontSize: 11, letterSpacing: "0.12em", color: MM.ghost,
      }}>
        <span>USER_INFO</span>
        <span style={{
          fontSize: 10, padding: "2px 8px",
          border: `1px solid ${user.accountType === "live" ? MM.green : MM.ghost}`,
          color: user.accountType === "live" ? MM.green : MM.ghost,
        }}>
          {user.accountType.toUpperCase()}
        </span>
      </div>

      {/* Body */}
      <div style={{ padding: 20 }}>
        {/* Name + ID row */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: "clamp(18px, 2.5vw, 28px)", fontWeight: 700, color: MM.text, letterSpacing: "-0.02em" }}>
            {user.name}
          </div>
          <div style={{ fontSize: 12, color: MM.dim, marginTop: 4 }}>
            {user.accountId}
          </div>
        </div>

        {/* Stats grid */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
          gap: 1,
          background: MM.border,
        }}>
          {[
            { label: "balance", value: `$${user.balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}`, accent: true },
            { label: "total_trades", value: String(user.totalTrades), accent: false },
            { label: "win_rate", value: `${winPct}%`, accent: false },
            { label: "joined", value: user.joinedAt, accent: false },
          ].map(({ label, value, accent }) => (
            <div key={label} style={{ background: MM.surface, padding: "14px 16px" }}>
              <Stat label={label} value={value} accent={accent || (label === "win_rate")} />
              {label === "win_rate" && (
                <div style={{ marginTop: 8, height: 3, background: MM.ghost, borderRadius: 0 }}>
                  <div style={{ height: 3, width: `${winPct}%`, background: winColor, transition: "width 0.8s ease" }} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
