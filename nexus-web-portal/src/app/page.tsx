"use client";

import { useEffect, useState } from "react";
import { fetchPlayerProfile, fetchStoreCatalog, PlayerProfile, StoreCatalog } from "@/lib/api";
import Link from "next/link";

export default function Home() {
  const [playerId, setPlayerId] = useState("salina_pilot_01");
  const [inputPlayerId, setInputPlayerId] = useState("");
  const [profile, setProfile] = useState<PlayerProfile | null>(null);
  const [catalog, setCatalog] = useState<StoreCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [purchaseStatus, setPurchaseStatus] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setErrorMessage(null);
      try {
        const [profileData, catalogData] = await Promise.all([
          fetchPlayerProfile(playerId),
          fetchStoreCatalog(),
        ]);
        setProfile(profileData);
        setCatalog(catalogData);
      } catch (err) {
        console.error("Error loading player session:", err);
        setErrorMessage(`Player ID "${playerId}" not found in database.`);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [playerId]);

  const handlePlayerLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputPlayerId.trim()) {
      setPlayerId(inputPlayerId.trim());
      setInputPlayerId("");
    }
  };

  const handleBuyCosmetic = async (itemKey: string, price: number) => {
    if (!profile) return;
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
          player_id: playerId,
          item_id: itemKey,
        }),
      });
      const data = await res.json();
      if (data.status === "SUCCESS" || res.ok) {
        setPurchaseStatus(`✅ Purchase successful! 13% NEX burned.`);
        // Refresh balance
        const updatedProfile = await fetchPlayerProfile(playerId);
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

            {/* Player Sign In Form */}
            <form onSubmit={handlePlayerLogin} className="flex gap-2">
              <input
                type="text"
                placeholder="Player ID (e.g. salina_pilot_01)"
                value={inputPlayerId}
                onChange={(e) => setInputPlayerId(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              />
              <button 
                type="submit" 
                className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold px-3 py-1.5 rounded transition"
              >
                Sign In
              </button>
            </form>

            <div className="bg-slate-900 border border-slate-800 px-4 py-2 rounded-lg text-right">
              <span className="text-xs text-slate-500 block uppercase tracking-wider">Active Account</span>
              <span className="font-mono text-cyan-300 font-semibold">{playerId}</span>
            </div>
          </div>
        </header>

        {errorMessage && (
          <div className="bg-red-950/60 border border-red-800 text-red-300 px-4 py-3 rounded-lg text-sm font-mono">
            ⚠️ {errorMessage}
          </div>
        )}

        {purchaseStatus && (
          <div className="bg-cyan-950/60 border border-cyan-800 text-cyan-300 px-4 py-3 rounded-lg text-sm font-mono">
            {purchaseStatus}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12 font-mono text-cyan-400">Syncing live database metrics...</div>
        ) : (
          <>
            {/* Player Metrics Grid */}
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
                  {profile?.nametag_style.display_name_formatted.replace("{username}", playerId) ?? playerId}
                </div>
              </div>
            </div>

            {/* Catalog Grid */}
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-slate-200">Available Cosmetics Catalog</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Global Core Cosmetics */}
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

                {/* Developer Cosmetics */}
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
