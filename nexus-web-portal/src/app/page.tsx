"use client";

import { useEffect, useState } from "react";
import { fetchPlayerProfile, fetchStoreCatalog, PlayerProfile, StoreCatalog } from "@/lib/api";
import Link from "next/link";

export default function Home() {
  const [profile, setProfile] = useState<PlayerProfile | null>(null);
  const [catalog, setCatalog] = useState<StoreCatalog | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [profileData, catalogData] = await Promise.all([
          fetchPlayerProfile("salina_pilot_01"),
          fetchStoreCatalog(),
        ]);
        setProfile(profileData);
        setCatalog(catalogData);
      } catch (err) {
        console.error("Error connecting to Render backend:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-cyan-400 flex items-center justify-center font-mono">
        Loading NEX Central Bank Telemetry...
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        <header className="flex justify-between items-center border-b border-slate-800 pb-6">
         <div>
         <h1 className="text-3xl font-bold tracking-tight text-cyan-400">NEXUS CENTRAL BANK</h1>
           <p className="text-slate-400 text-sm">Universal Game Economy & Multi-Game Cosmetic Portal</p>
        </div>
        <div className="flex items-center gap-4">
         <Link href="/developers" className="bg-purple-900/50 hover:bg-purple-900 border border-purple-700 text-purple-300 text-sm font-bold px-4 py-2 rounded-lg transition">
      Dev Studio Portal →
        </Link>
         <div className="bg-slate-900 border border-slate-800 px-4 py-2 rounded-lg text-right">
         <span className="text-xs text-slate-500 block uppercase tracking-wider">Pilot Account</span>
          <span className="font-mono text-cyan-300 font-semibold">{profile?.player_id}</span>
       </div>
    </div>
  </header>

        {/* Player Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 backdrop-blur">
            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Spendable Balance</span>
            <div className="text-4xl font-extrabold text-emerald-400 mt-2 font-mono">
              {profile?.spendable_nex.toFixed(2)} <span className="text-xl text-emerald-500">NEX</span>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 backdrop-blur">
            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Lifetime Earned</span>
            <div className="text-4xl font-extrabold text-cyan-400 mt-2 font-mono">
              {profile?.total_nex_earned.toFixed(2)} <span className="text-xl text-cyan-500">NEX</span>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 backdrop-blur">
            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">In-Game Display</span>
            <div 
              className="text-xl font-bold mt-3 font-mono" 
              style={{ color: profile?.nametag_style.text_color || "#00F0FF" }}
            >
              {profile?.nametag_style.display_name_formatted.replace("{username}", "Pilot")}
            </div>
          </div>
        </div>

        {/* Cosmetic Store Catalogue */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-slate-200">Global & Developer Cosmetics Catalog</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Global Items */}
            {catalog?.global_cosmetics.map((item) => (
              <div key={item.item_id} className="bg-slate-900 border border-slate-800 p-5 rounded-xl space-y-3">
                <div className="flex justify-between items-start">
                  <h3 className="font-bold text-lg text-slate-100">{item.name}</h3>
                  <span className="bg-cyan-950 text-cyan-400 text-xs font-mono font-bold px-2.5 py-1 rounded border border-cyan-800">
                    {item.price_nex} NEX
                  </span>
                </div>
                <p className="text-slate-400 text-sm">{item.description}</p>
              </div>
            ))}

            {/* Third Party Developer Items */}
            {catalog?.developer_cosmetics.map((item) => (
              <div key={item.item_key} className="bg-slate-900 border border-purple-900/50 p-5 rounded-xl space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-bold text-lg text-purple-200">{item.name}</h3>
                    <span className="text-xs text-purple-400 uppercase font-mono">{item.game_id}</span>
                  </div>
                  <span className="bg-purple-950 text-purple-300 text-xs font-mono font-bold px-2.5 py-1 rounded border border-purple-800">
                    {item.price_nex} NEX
                  </span>
                </div>
                <p className="text-slate-400 text-sm">Category: {item.category}</p>
              </div>
            ))}
          </div>
        </div>

      </div>
    </main>
  );
}
