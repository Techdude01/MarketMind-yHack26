"use client";

import { useCallback, useEffect, useState } from "react";

const defaultBase =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:5001";

function apiUrl(base: string, path: string): string {
  return `${base.replace(/\/$/, "")}${path}`;
}

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
  const [baseUrl, setBaseUrl] = useState(defaultBase);
  const [markets, setMarkets] = useState<DbMarket[]>([]);
  const [loading, setLoading] = useState<"list" | "ingest" | null>(null);
  const [error, setError] = useState<string>("");

  const loadMarkets = useCallback(async () => {
    setLoading("list");
    setError("");
    try {
      const res = await fetch(apiUrl(baseUrl, "/markets"));
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
      setLoading(null);
    }
  }, [baseUrl]);

  useEffect(() => {
    void loadMarkets();
  }, [loadMarkets]);

  const refreshFromGamma = useCallback(async () => {
    setLoading("ingest");
    setError("");
    try {
      const res = await fetch(apiUrl(baseUrl, "/ingest/markets"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
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
        return;
      }
      await loadMarkets();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  }, [baseUrl, loadMarkets]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 font-sans">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            {title}
          </h1>
          <p className="mt-1 max-w-xl text-sm text-zinc-600 dark:text-zinc-400">
            Data from Postgres via <code className="text-xs">GET /markets</code>.
            Use Refresh to run <code className="text-xs">POST /ingest/markets</code>{" "}
            (Polymarket Gamma → DB).
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex flex-col gap-1 text-xs text-zinc-600 dark:text-zinc-400">
            API base
            <input
              type="url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              className="w-56 rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            />
          </label>
          <button
            type="button"
            disabled={loading !== null}
            onClick={() => void loadMarkets()}
            className="rounded border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-800 disabled:opacity-50 dark:border-zinc-600 dark:text-zinc-200"
          >
            Reload
          </button>
          <button
            type="button"
            disabled={loading !== null}
            onClick={() => void refreshFromGamma()}
            className="rounded bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
          >
            Refresh Markets
          </button>
        </div>
      </div>

      {error ? (
        <p className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      ) : null}

      {loading === "list" && markets.length === 0 ? (
        <p className="text-sm text-zinc-500">Loading markets…</p>
      ) : null}

      {loading === "ingest" ? (
        <p className="mb-4 text-sm text-zinc-500">Ingesting from Polymarket…</p>
      ) : null}

      {!loading && markets.length === 0 && !error ? (
        <p className="text-sm text-zinc-500">
          No rows yet. Click <strong>Refresh Markets</strong> to ingest from Gamma.
        </p>
      ) : null}

      {markets.length > 0 ? (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {markets.map((m) => (
            <li
              key={m.polymarket_id}
              className="flex flex-col overflow-hidden rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950"
            >
              <div className="relative aspect-[2/1] w-full bg-zinc-100 dark:bg-zinc-900">
                {m.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={m.image_url}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-xs text-zinc-400">
                    No image
                  </div>
                )}
              </div>
              <div className="flex flex-1 flex-col gap-2 p-3">
                <p className="text-sm font-medium leading-snug text-zinc-900 dark:text-zinc-50">
                  {m.question}
                </p>
                <div className="flex flex-wrap gap-2 text-xs">
                  {m.active ? (
                    <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-900 dark:bg-emerald-900 dark:text-emerald-100">
                      Active
                    </span>
                  ) : null}
                  {m.closed ? (
                    <span className="rounded bg-zinc-200 px-1.5 py-0.5 text-zinc-800 dark:bg-zinc-700 dark:text-zinc-200">
                      Closed
                    </span>
                  ) : null}
                  {m.featured ? (
                    <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-900 dark:bg-amber-900 dark:text-amber-100">
                      Featured
                    </span>
                  ) : null}
                </div>
                <dl className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs text-zinc-600 dark:text-zinc-400">
                  <dt>Volume</dt>
                  <dd className="text-right font-mono text-zinc-900 dark:text-zinc-200">
                    {formatUsd(m.volume_num ?? m.volume ?? null)}
                  </dd>
                  <dt>Last trade</dt>
                  <dd className="text-right font-mono text-zinc-900 dark:text-zinc-200">
                    {formatPrice(m.last_trade_price)}
                  </dd>
                  <dt>Ends</dt>
                  <dd className="text-right">{formatEndDate(m.end_date)}</dd>
                </dl>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
