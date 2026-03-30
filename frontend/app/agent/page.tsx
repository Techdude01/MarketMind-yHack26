import Nav from "../components/landing/Nav";
import { AgentSearchPanel } from "../components/AgentSearchPanel";

export default function AgentPage() {
  return (
    <div
      style={{
        background: "#0C0C0E",
        minHeight: "100vh",
        color: "#E4E4E7",
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      <Nav />
      <div style={{ paddingTop: 48 }}>
        <AgentSearchPanel />
      </div>
    </div>
  );
}
