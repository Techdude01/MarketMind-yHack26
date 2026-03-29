import Link from "next/link";

import { StoredMarketsPanel } from "../components/StoredMarketsPanel";

export default function MarketsPage() {
  return (
    <>
      <div className="border-b border-zinc-200 px-4 py-2 dark:border-zinc-800">
        <Link
          href="/"
          className="text-sm text-zinc-600 underline dark:text-zinc-400"
        >
          ← Home
        </Link>
      </div>
      <StoredMarketsPanel title="Markets" />
    </>
  );
}
