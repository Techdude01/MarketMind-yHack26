"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

const defaultBase =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:5000";

export default function Home() {
  const [baseUrl, setBaseUrl] = useState(defaultBase);
  const [output, setOutput] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const run = useCallback(
    async (path: string, init?: RequestInit) => {
      setLoading(true);
      setOutput("");
      try {
        const res = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, {
          ...init,
          headers: {
            "Content-Type": "application/json",
            ...init?.headers,
          },
        });
        const text = await res.text();
        let parsed: unknown;
        try {
          parsed = JSON.parse(text);
        } catch {
          parsed = text;
        }
        setOutput(JSON.stringify(parsed, null, 2));
      } catch (e) {
        setOutput(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    },
    [baseUrl],
  );

  return (
    <main style={{ padding: "1.5rem", fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ marginTop: 0 }}>MarketMind stack check</h1>
      <p style={{ marginBottom: "1rem" }}>
        <Link href="/markets" style={{ textDecoration: "underline" }}>
          Test Polymarket API → /markets
        </Link>
      </p>
      <p style={{ maxWidth: "40rem" }}>
        API base (from{" "}
        <code style={{ fontSize: "0.9em" }}>NEXT_PUBLIC_API_BASE_URL</code>):
      </p>
      <input
        type="url"
        value={baseUrl}
        onChange={(e) => setBaseUrl(e.target.value)}
        style={{ width: "100%", maxWidth: "32rem", marginBottom: "1rem" }}
      />
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
        <button type="button" disabled={loading} onClick={() => run("/health")}>
          GET /health
        </button>
        <button
          type="button"
          disabled={loading}
          onClick={() => run("/db/health")}
        >
          GET /db/health
        </button>
        <button type="button" disabled={loading} onClick={() => run("/db/read")}>
          GET /db/read
        </button>
        <button
          type="button"
          disabled={loading}
          onClick={() =>
            run("/db/write", {
              method: "POST",
              body: JSON.stringify({
                message: `hello from browser ${new Date().toISOString()}`,
              }),
            })
          }
        >
          POST /db/write
        </button>
      </div>
      <pre
        style={{
          marginTop: "1rem",
          padding: "0.75rem",
          background: "#f4f4f5",
          overflow: "auto",
          maxWidth: "48rem",
        }}
      >
        {loading ? "…" : output || "—"}
      </pre>
    </main>
  );
}
