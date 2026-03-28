"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

const defaultBase =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:5000";

type MarketRow = {
  condition_id?: string;
  question?: string;
  accepting_orders?: boolean;
  tokens?: Array<{ token_id?: string }>;
};

function apiPath(base: string, path: string) {
  return `${base.replace(/\/$/, "")}${path}`;
}

export default function MarketsPage() {
  const [baseUrl, setBaseUrl] = useState(defaultBase);
  const [limit, setLimit] = useState(15);
  const [markets, setMarkets] = useState<MarketRow[]>([]);
  const [nextCursor, setNextCursor] = useState<string>("");
  const [detail, setDetail] = useState<unknown>(null);
  const [orderbook, setOrderbook] = useState<unknown>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<string | null>(null);

  const loadMarkets = useCallback(
    async (cursor?: string) => {
      setLoading("markets");
      setError("");
      try {
        const params = new URLSearchParams();
        params.set("limit", String(limit));
        if (cursor) params.set("next_cursor", cursor);
        const res = await fetch(
          apiPath(baseUrl, `/markets?${params.toString()}`),
        );
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          setError(
            typeof body?.error === "string"
              ? body.error
              : `HTTP ${res.status}`,
          );
          return;
        }
        const data = (body as { data?: MarketRow[]; next_cursor?: string })
          .data;
        const nc = (body as { next_cursor?: string }).next_cursor ?? "";
        if (cursor) {
          setMarkets((prev) => [...prev, ...(data ?? [])]);
        } else {
          setMarkets(data ?? []);
        }
        setNextCursor(nc);
        setDetail(null);
        setOrderbook(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(null);
      }
    },
    [baseUrl, limit],
  );

  const loadDetail = useCallback(
    async (conditionId: string) => {
      setLoading("detail");
      setError("");
      try {
        const res = await fetch(
          apiPath(baseUrl, `/markets/${encodeURIComponent(conditionId)}`),
        );
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          setError(
            typeof body?.error === "string"
              ? body.error
              : `HTTP ${res.status}`,
          );
          setDetail(null);
          return;
        }
        setDetail(body);
        setOrderbook(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setDetail(null);
      } finally {
        setLoading(null);
      }
    },
    [baseUrl],
  );

  const loadOrderbook = useCallback(
    async (tokenId: string) => {
      setLoading("book");
      setError("");
      try {
        const res = await fetch(
          apiPath(
            baseUrl,
            `/markets/orderbook/${encodeURIComponent(tokenId)}`,
          ),
        );
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          setError(
            typeof body?.error === "string"
              ? body.error
              : `HTTP ${res.status}`,
          );
          setOrderbook(null);
          return;
        }
        setOrderbook(body);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setOrderbook(null);
      } finally {
        setLoading(null);
      }
    },
    [baseUrl],
  );

  const firstTokenId = useMemo(() => {
    if (!detail || typeof detail !== "object") return null;
    const tokens = (detail as { tokens?: Array<{ token_id?: string }> })
      .tokens;
    if (!tokens?.length) return null;
    return tokens.find((t) => t.token_id)?.token_id ?? null;
  }, [detail]);

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 font-sans">
      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Polymarket markets
          </h1>
          <p className="mt-1 max-w-xl text-sm text-zinc-600 dark:text-zinc-400">
            Calls the Flask routes in{" "}
            <code className="rounded bg-zinc-100 px-1 text-xs dark:bg-zinc-800">
              backend/app/routes/markets.py
            </code>{" "}
            — list, detail, and order book. Requires a running backend with
            network access to Polymarket.
          </p>
        </div>
        <Link
          href="/"
          className="text-sm text-zinc-600 underline dark:text-zinc-400"
        >
          ← Stack check
        </Link>
      </div>

      <section className="mb-8 space-y-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
        <label className="block text-sm font-medium">API base URL</label>
        <input
          type="url"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          className="w-full max-w-md rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-950"
        />
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm">
            Limit{" "}
            <input
              type="number"
              min={1}
              max={100}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value) || 20)}
              className="ml-1 w-16 rounded border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700"
            />
          </label>
          <button
            type="button"
            disabled={!!loading}
            onClick={() => loadMarkets()}
            className="rounded bg-zinc-900 px-3 py-1.5 text-sm text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
          >
            GET /markets
          </button>
          {nextCursor ? (
            <button
              type="button"
              disabled={!!loading}
              onClick={() => loadMarkets(nextCursor)}
              className="rounded border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700"
            >
              Next page
            </button>
          ) : null}
        </div>
      </section>

      {error ? (
        <p className="mb-4 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      ) : null}

      <div className="grid gap-8 lg:grid-cols-2">
        <section>
          <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-zinc-500">
            Markets ({markets.length})
          </h2>
          {loading === "markets" && markets.length === 0 ? (
            <p className="text-sm text-zinc-500">Loading…</p>
          ) : markets.length === 0 ? (
            <p className="text-sm text-zinc-500">
              Load markets to see rows here.
            </p>
          ) : (
            <ul className="max-h-[32rem] space-y-2 overflow-y-auto pr-1 text-sm">
              {markets.map((m, idx) => {
                const cid = m.condition_id ?? "";
                const tid =
                  m.tokens?.find((t) => t.token_id)?.token_id ?? null;
                return (
                  <li
                    key={cid || `market-${idx}`}
                    className="rounded border border-zinc-200 p-3 dark:border-zinc-800"
                  >
                    <p className="font-medium leading-snug">
                      {m.question ?? "(no question)"}
                    </p>
                    <p className="mt-1 break-all font-mono text-xs text-zinc-500">
                      {cid}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {m.accepting_orders ? (
                        <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">
                          accepting orders
                        </span>
                      ) : null}
                      <button
                        type="button"
                        disabled={!!loading || !cid}
                        onClick={() => loadDetail(cid)}
                        className="text-xs underline disabled:opacity-50"
                      >
                        Detail
                      </button>
                      {tid ? (
                        <button
                          type="button"
                          disabled={!!loading}
                          onClick={() => loadOrderbook(tid)}
                          className="text-xs underline disabled:opacity-50"
                        >
                          Order book
                        </button>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section className="space-y-6">
          <div>
            <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-zinc-500">
              GET /markets/&lt;condition_id&gt;
            </h2>
            {loading === "detail" ? (
              <p className="text-sm text-zinc-500">Loading…</p>
            ) : detail ? (
              <pre className="max-h-64 overflow-auto rounded border border-zinc-200 bg-zinc-50 p-3 text-xs dark:border-zinc-800 dark:bg-zinc-950">
                {JSON.stringify(detail, null, 2)}
              </pre>
            ) : (
              <p className="text-sm text-zinc-500">
                Choose <strong>Detail</strong> on a market.
              </p>
            )}
            {firstTokenId ? (
              <button
                type="button"
                disabled={!!loading}
                onClick={() => loadOrderbook(firstTokenId)}
                className="mt-2 text-xs underline"
              >
                Order book (first outcome token)
              </button>
            ) : null}
          </div>

          <div>
            <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-zinc-500">
              GET /markets/orderbook/&lt;token_id&gt;
            </h2>
            {loading === "book" ? (
              <p className="text-sm text-zinc-500">Loading…</p>
            ) : orderbook ? (
              <pre className="max-h-64 overflow-auto rounded border border-zinc-200 bg-zinc-50 p-3 text-xs dark:border-zinc-800 dark:bg-zinc-950">
                {JSON.stringify(orderbook, null, 2)}
              </pre>
            ) : (
              <p className="text-sm text-zinc-500">
                Use <strong>Order book</strong> on a row or from detail.
              </p>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
