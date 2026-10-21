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

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [profileData, catalogData] = await Promise.all([
          fetchPlayerProfile(playerId),
          fetchStoreCatalog(),
        ]);
        setProfile(profileData);
        setCatalog(catalogData);
      } catch (err) {
        console.error("Error loading player session:", err);
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
            {/* Player Session Selector */}
            <form onSubmit={handlePlayerLogin} className="flex gap-2">
              <input
                type="text"
                placeholder="Enter Player ID..."
                value={inputPlayerId}
                onChange={(e) => setInputPlayerId(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              />
              <button type="submit" className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold px-3 py-1.5 rounded transition">
                Load Session
              </button>
            </form>

            <div className="bg-slate-900 border border-slate-800 px-4 py-2 rounded-lg text-right">
              <span className="text-xs text-slate-500 block uppercase tracking-wider">Active ID</span>
              <span className="font-mono text-cyan-300 font-semibold">{playerId}</span>
            </div>
          </div>
        </header>

        {loading ? (
          <div className="text-center py-12 font-mono text-cyan-400">Syncing live database metrics...</div>
        ) : (
          <>
            {/* Player Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Spendable NEX</span>
                <div className="text-3xl font-extrabold text-emerald-400 mt-2 font-mono">
                  {profile?.spendable_nex.toFixed(2)}
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Lifetime Earned</span>
                <div className="text-3xl font-extrabold text-cyan-400 mt-2 font-mono">
                  {profile?.total_nex_earned.toFixed(2)}
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Hours Logged</span>
                <div className="text-3xl font-extrabold text-purple-400 mt-2 font-mono">
                  {profile?.total_hours_played.toFixed(1)} hrs
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">In-Game Display</span>
                <div 
                  className="text-lg font-bold mt-2 font-mono truncate" 
                  style={{ color: profile?.nametag_style.text_color || "#00F0FF" }}
                >
                  {profile?.nametag_style.display_name_formatted.replace("{username}", playerId)}
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
                    <span className="bg-cyan-950 text-cyan-400 text-xs font-mono font-bold px-3 py-1.5 rounded border border-cyan-800">
                      {item.price_nex} NEX
                    </span>
                  </div>
                ))}
                {catalog?.developer_cosmetics.map((item) => (
                  <div key={item.item_key} className="bg-slate-900 border border-purple-900/50 p-5 rounded-xl flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-purple-200">{item.name}</h3>
                      <span className="text-xs text-purple-400 uppercase font-mono">{item.game_id}</span>
                    </div>
                    <span className="bg-purple-950 text-purple-300 text-xs font-mono font-bold px-3 py-1.5 rounded border border-purple-800">
                      {item.price_nex} NEX
                    </span>
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
