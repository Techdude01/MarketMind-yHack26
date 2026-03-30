import Nav from "../components/landing/Nav";
import { StoredMarketsPanel } from "../components/StoredMarketsPanel";

export default function MarketsPage() {
  return (
    <div style={{ background: "#0C0C0E", minHeight: "100vh", color: "#E4E4E7", fontFamily: "'JetBrains Mono', monospace" }}>
      <Nav />
      <div style={{ paddingTop: 48 }}>
        <StoredMarketsPanel />
      </div>
    </div>
  );
}
