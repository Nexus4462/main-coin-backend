"use client";

import { useState } from "react";
import { fetchPlayerProfile, fetchStoreCatalog, PlayerProfile, StoreCatalog } from "@/lib/api";
import Link from "next/link";

export default function Home() {
  const [inputPlayerId, setInputPlayerId] = useState("");
  const [activePlayerId, setActivePlayerId] = useState<string | null>(null);
  const [profile, setProfile] = useState<PlayerProfile | null>(null);
  const [catalog, setCatalog] = useState<StoreCatalog | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [purchaseStatus, setPurchaseStatus] = useState<string | null>(null);

  const handlePlayerLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputPlayerId.trim()) return;

    const targetId = inputPlayerId.trim();
    setLoading(true);
    setErrorMessage(null);
    setPurchaseStatus(null);

    try {
      const [profileData, catalogData] = await Promise.all([
        fetchPlayerProfile(targetId),
        fetchStoreCatalog(),
      ]);
      setProfile(profileData);
      setCatalog(catalogData);
      setActivePlayerId(targetId);
    } catch (err) {
      console.error("Error loading player session:", err);
      setErrorMessage(`Player ID "${targetId}" not found in database.`);
      setActivePlayerId(null);
      setProfile(null);
    } finally {
      setLoading(false);
    }
  };

  const handleBuyCosmetic = async (itemKey: string, price: number) => {
    if (!profile || !activePlayerId) return;
    if (profile.spendable_nex < price) {
      setPurchaseStatus(`❌ Insufficient NEX balance! Need ${price} NEX.`);
      return;
    }

    setPurchaseStatus(`Purchasing ${itemKey}...`);
    try {
      const res = await fetch("https://main-coin-backend.onrender.com/api/v1/store/buy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_id: activePlayerId,
          item_id: itemKey,
        }),
      });
      const data = await res.json();
      if (data.status === "SUCCESS" || res.ok) {
        setPurchaseStatus(`✅ Purchase successful! 13% NEX burned.`);
        const updatedProfile = await fetchPlayerProfile(activePlayerId);
        setProfile(updatedProfile);
      } else {
        setPurchaseStatus(`❌ ${data.detail || "Purchase failed."}`);
      }
    } catch (err) {
      setPurchaseStatus("❌ Network error connecting to backend.");
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Navigation Header */}
        <header className="flex justify-between items-center border-b border-slate-800 pb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-cyan-400">NEXUS PLAYER PORTAL</h1>
            <p className="text-slate-400 text-sm">Authenticated Live Player Progress & Store</p>
          </div>

          <div className="flex items-center gap-4">
            <Link 
              href="/developers" 
              className="bg-purple-900/50 hover:bg-purple-900 border border-purple-700 text-purple-300 text-sm font-bold px-4 py-2 rounded-lg transition"
            >
              Dev Studio Portal →
            </Link>

            {/* Active Session Badge */}
            {activePlayerId && (
              <div className="bg-slate-900 border border-slate-800 px-4 py-2 rounded-lg text-right">
                <span className="text-xs text-slate-500 block uppercase tracking-wider">Active Account</span>
                <span className="font-mono text-cyan-300 font-semibold">{activePlayerId}</span>
              </div>
            )}
          </div>
        </header>

        {/* Lock Screen / Sign In Form */}
        {!activePlayerId ? (
          <div className="max-w-md mx-auto my-16 bg-slate-900 border border-slate-800 rounded-2xl p-8 space-y-6 text-center">
            <h2 className="text-xl font-bold text-slate-200">Authenticate Player Session</h2>
            <p className="text-slate-400 text-sm">Enter your Player ID to access your spendable balance and store catalog.</p>
            
            <form onSubmit={handlePlayerLogin} className="space-y-4">
              <input
                type="text"
                placeholder="Enter Player ID (e.g. salina_pilot_01)"
                value={inputPlayerId}
                onChange={(e) => setInputPlayerId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              />
              <button 
                type="submit" 
                disabled={loading}
                className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-3 rounded-lg transition disabled:opacity-50"
              >
                {loading ? "Authenticating..." : "Sign In to Portal"}
              </button>
            </form>

            {errorMessage && (
              <div className="bg-red-950/60 border border-red-800 text-red-300 px-4 py-3 rounded-lg text-xs font-mono text-left">
                ⚠️ {errorMessage}
              </div>
            )}
          </div>
        ) : (
          /* Unlocked Player Dashboard */
          <>
            {purchaseStatus && (
              <div className="bg-cyan-950/60 border border-cyan-800 text-cyan-300 px-4 py-3 rounded-lg text-sm font-mono">
                {purchaseStatus}
              </div>
            )}

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Spendable NEX</span>
                <div className="text-3xl font-extrabold text-emerald-400 mt-2 font-mono">
                  {profile?.spendable_nex.toFixed(2) ?? "0.00"}
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Lifetime Earned</span>
                <div className="text-3xl font-extrabold text-cyan-400 mt-2 font-mono">
                  {profile?.total_nex_earned.toFixed(2) ?? "0.00"}
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Hours Logged</span>
                <div className="text-3xl font-extrabold text-purple-400 mt-2 font-mono">
                  {profile?.total_hours_played.toFixed(1) ?? "0.0"} hrs
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">In-Game Display</span>
                <div 
                  className="text-lg font-bold mt-2 font-mono truncate" 
                  style={{ color: profile?.nametag_style.text_color || "#00F0FF" }}
                >
                  {profile?.nametag_style.display_name_formatted.replace("{username}", activePlayerId) ?? activePlayerId}
                </div>
              </div>
            </div>

            {/* Catalog Grid */}
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-slate-200">Available Cosmetics Catalog</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {catalog?.global_cosmetics.map((item) => (
                  <div key={item.item_id} className="bg-slate-900 border border-slate-800 p-5 rounded-xl flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-slate-100">{item.name}</h3>
                      <p className="text-slate-400 text-xs mt-1">{item.description}</p>
                    </div>
                    <button
                      onClick={() => handleBuyCosmetic(item.item_id, item.price_nex)}
                      className="bg-cyan-950 hover:bg-cyan-900 text-cyan-400 text-xs font-mono font-bold px-3 py-2 rounded border border-cyan-800 transition"
                    >
                      Buy for {item.price_nex} NEX
                    </button>
                  </div>
                ))}

                {catalog?.developer_cosmetics.map((item) => (
                  <div key={item.item_key} className="bg-slate-900 border border-purple-900/50 p-5 rounded-xl flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-purple-200">{item.name}</h3>
                      <span className="text-xs text-purple-400 uppercase font-mono">{item.game_id}</span>
                    </div>
                    <button
                      onClick={() => handleBuyCosmetic(item.item_key, item.price_nex)}
                      className="bg-purple-950 hover:bg-purple-900 text-purple-300 text-xs font-mono font-bold px-3 py-2 rounded border border-purple-800 transition"
                    >
                      Buy for {item.price_nex} NEX
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

      </div>
    </main>
  );
}
