"use client";
import Link from "next/link";
import { useEffect, useState } from "react";

const S: Record<string, React.CSSProperties> = {
  nav: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    height: 48,
    zIndex: 100,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 24px",
    borderBottom: "1px solid rgba(255,255,255,0.18)",
    transition: "background 0.3s, backdrop-filter 0.3s",
    fontFamily: "'JetBrains Mono', monospace",
  },
  logo: { display: "flex", alignItems: "center", gap: 8 },
  mm: { color: "#4ADE80", fontSize: 13, fontWeight: 500 },
  name: { color: "#E4E4E7", fontSize: 13, fontWeight: 500 },
  links: { display: "flex", alignItems: "center", gap: 20 },
  link: {
    color: "#71717A",
    fontSize: 12,
    fontWeight: 400,
    background: "none",
    border: "none",
    cursor: "pointer",
    fontFamily: "inherit",
    padding: 0,
    transition: "color 0.2s",
    textDecoration: "none",
  },
  btn: {
    color: "#71717A",
    fontSize: 12,
    fontWeight: 400,
    background: "none",
    border: "1px solid rgba(255,255,255,0.18)",
    borderRadius: 0,
    padding: "6px 14px",
    cursor: "pointer",
    fontFamily: "inherit",
    transition: "border-color 0.2s, color 0.2s",
  },
  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.55)",
    backdropFilter: "blur(2px)",
    WebkitBackdropFilter: "blur(2px)",
    zIndex: 1000,
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    padding: 16,
  },
  modal: {
    width: "100%",
    maxWidth: 520,
    border: "1px solid rgba(74,222,128,0.35)",
    background:
      "linear-gradient(180deg, rgba(12,12,14,0.98) 0%, rgba(17,17,20,0.98) 100%)",
    boxShadow: "0 12px 40px rgba(0,0,0,0.5)",
    padding: 18,
    fontFamily: "'JetBrains Mono', monospace",
  },
  modalHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 14,
  },
  modalTitle: {
    color: "#4ADE80",
    fontSize: 13,
    letterSpacing: "0.02em",
  },
  closeBtn: {
    ...({
      background: "none",
      border: "1px solid rgba(255,255,255,0.2)",
      color: "#A1A1AA",
      padding: "4px 10px",
      cursor: "pointer",
      fontFamily: "inherit",
      fontSize: 11,
    } as React.CSSProperties),
  },
  card: {
    border: "1px solid rgba(255,255,255,0.12)",
    padding: 12,
    marginBottom: 12,
  },
  label: { color: "#71717A", fontSize: 11, marginBottom: 6 },
  value: {
    color: "#E4E4E7",
    fontSize: 12,
    wordBreak: "break-all",
    lineHeight: 1.5,
  },
  actions: { display: "flex", gap: 10, marginTop: 8, flexWrap: "wrap" },
  actionBtn: {
    border: "1px solid rgba(255,255,255,0.2)",
    background: "none",
    color: "#A1A1AA",
    padding: "6px 10px",
    cursor: "pointer",
    fontFamily: "inherit",
    fontSize: 11,
  },
  actionBtnPrimary: {
    border: "1px solid rgba(74,222,128,0.45)",
    color: "#4ADE80",
  },
  tiny: { color: "#71717A", fontSize: 11, marginTop: 8 },
};

const navLinks = [
  { label: "_markets", href: "/markets" },
  { label: "_agent", href: "/markets" },
  { label: "_dashboard", href: "/dashboard" },
];

function shortAddress(addr: string) {
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [walletLabel, setWalletLabel] = useState("> connect_wallet");
  const [showProfileModal, setShowProfileModal] = useState(false);

  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", h, { passive: true });
    return () => window.removeEventListener("scroll", h);
  }, []);

  useEffect(() => {
    const syncWallet = async () => {
      try {
        if (sessionStorage.getItem("wallet_disconnected")) return;
        const eth = (window as any).ethereum;
        if (!eth) return;
        const accounts = await eth.request({ method: "eth_accounts" });
        const addr = accounts?.[0];
        if (!addr) return;
        setWalletAddress(addr);
        setWalletLabel(`> ${shortAddress(addr)}`);
      } catch {
        // no-op
      }
    };
    syncWallet();
  }, []);

  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowProfileModal(false);
    };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, []);

  const onConnectWallet = async () => {
    try {
      const eth = (window as any).ethereum;
      if (!eth) {
        setWalletLabel("> install_metamask");
        return;
      }

      if (walletAddress && !sessionStorage.getItem("wallet_disconnected")) {
        setShowProfileModal(true);
        return;
      }

      if (sessionStorage.getItem("wallet_disconnected")) {
        try {
          await eth.request({
            method: "wallet_requestPermissions",
            params: [{ eth_accounts: {} }],
          });
        } catch {
          setWalletLabel("> connect_wallet");
          return;
        }
      }

      const accounts = await eth.request({ method: "eth_requestAccounts" });
      const addr = accounts?.[0];
      if (!addr) {
        setWalletLabel("> connect_wallet");
        return;
      }

      sessionStorage.removeItem("wallet_disconnected");
      setWalletAddress(addr);
      setWalletLabel(`> ${shortAddress(addr)}`);
      setShowProfileModal(true);
      window.location.reload();
    } catch (err: any) {
      if (err?.code === 4001) setWalletLabel("> rejected");
      else setWalletLabel("> connect_failed");
    }
  };

  const onDisconnectLocal = () => {
    sessionStorage.setItem("wallet_disconnected", "true");
    setWalletAddress(null);
    setWalletLabel("> connect_wallet");
    setShowProfileModal(false);
    window.location.reload();
  };

  return (
    <>
      <nav
        style={{
          ...S.nav,
          background: scrolled ? "rgba(12,12,14,0.92)" : "transparent",
          backdropFilter: scrolled ? "blur(10px)" : "none",
          WebkitBackdropFilter: scrolled ? "blur(10px)" : "none",
        }}
      >
        <Link href="/" style={{ ...S.logo, textDecoration: "none" }}>
          <span style={S.mm}>[MM]</span>
          <span style={S.name}>MarketMind</span>
        </Link>
        <div style={S.links}>
          {navLinks.map(({ label, href }) => (
            <Link
              key={label}
              href={href}
              style={S.link}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#4ADE80")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "#71717A")}
            >
              {label}
            </Link>
          ))}
          <button style={S.btn} onClick={onConnectWallet}>
            {walletLabel}
          </button>
        </div>
      </nav>
      {showProfileModal && walletAddress && (
        <div style={S.overlay} onClick={() => setShowProfileModal(false)}>
          <div style={S.modal} onClick={(e) => e.stopPropagation()}>
            <div style={S.modalHeader}>
              <div style={S.modalTitle}>{"> wallet_profile"}</div>
              <button
                style={S.closeBtn}
                onClick={() => setShowProfileModal(false)}
              >
                close
              </button>
            </div>
            <div style={S.card}>
              <div style={S.label}>connected_address</div>
              <div style={S.value}>{walletAddress}</div>
            </div>
            <div style={S.actions}>
              <button
                style={{ ...S.actionBtn, ...S.actionBtnPrimary }}
                onClick={() => navigator.clipboard.writeText(walletAddress)}
              >
                copy_address
              </button>
              <button style={S.actionBtn} onClick={onDisconnectLocal}>
                disconnect_ui
              </button>
            </div>
            <div style={S.tiny}>
              This disconnect only resets local UI state. Wallet remains
              connected in MetaMask.
            </div>
          </div>
        </div>
      )}
    </>
  );
}