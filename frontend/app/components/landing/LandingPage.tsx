"use client";

import { useEffect } from "react";
import AnalysisPreview from "./AnalysisPreview";
import Footer from "./Footer";
import Hero from "./Hero";
import MetricsGrid from "./MetricsGrid";
import Nav from "./Nav";
import ProcessSection from "./ProcessSection";
import SignalStrip from "./SignalStrip";

// Inline SVG data URI for the noise filter — feTurbulence + feColorMatrix
const NOISE_SVG = `<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'>
  <filter id='noise'>
    <feTurbulence
      type='fractalNoise'
      baseFrequency='0.65'
      numOctaves='4'
      stitchTiles='stitch'/>
    <feColorMatrix type='saturate' values='0'/>
    <feComponentTransfer>
      <feFuncA type='linear' slope='0.9'/>
    </feComponentTransfer>
  </filter>
  <rect width='200' height='200' filter='url(#noise)' opacity='1' fill='white'/>
</svg>`;

const noiseUrl = `url("data:image/svg+xml,${encodeURIComponent(NOISE_SVG)}")`;

const grainStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  zIndex: 9999,
  pointerEvents: "none",
  backgroundImage: noiseUrl,
  backgroundRepeat: "repeat",
  backgroundSize: "200px 200px",
  opacity: 0.18,
  mixBlendMode: "screen",
};

export default function LandingPage() {
  useEffect(() => {
    document.body.style.backgroundColor = "#0C0C0E";
    document.body.style.color = "#E4E4E7";
    return () => {
      document.body.style.backgroundColor = "";
      document.body.style.color = "";
    };
  }, []);

  return (
    <div style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace", background: "#0C0C0E", color: "#E4E4E7", position: "relative" }}>
      {/* Film grain overlay — SVG feTurbulence, fixed, non-interactive */}
      <div style={grainStyle} aria-hidden="true" />
      <Nav />
      <Hero />
      <SignalStrip />
      <ProcessSection />
      <MetricsGrid />
      <AnalysisPreview />
      <Footer />
    </div>
  );
}
