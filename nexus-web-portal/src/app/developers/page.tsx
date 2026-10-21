"use client";

import { useState } from "react";
import Link from "next/link";

export default function DevelopersPage() {
  const [developerKey, setDeveloperKey] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [keyError, setKeyError] = useState<string | null>(null);

  const [gameId, setGameId] = useState("game_palworld_mech_arena");
  const [itemId, setItemId] = useState("");
  const [priceNex, setPriceNex] = useState(100);
  const [displayName, setDisplayName] = useState("");
  const [category, setCategory] = useState("Skin");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleDevLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (developerKey === "nexus_dev_secret_2026") {
      setIsAuthenticated(true);
      setKeyError(null);
    } else {
      setKeyError("❌ Invalid Developer Key. Access Denied.");
    }
  };

  const handlePublish = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMessage("Publishing to NEXUS Ecosystem...");

    try {
      const res = await fetch("https://main-coin-backend.onrender.com/api/v1/developer/cosmetics", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Developer-Key": developerKey,
        },
        body: JSON.stringify({
          game_id: gameId,
          item_id: itemId,
          price_nex: priceNex,
          display_name: displayName,
          category: category,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setStatusMessage(`✅ Published! Item Key: ${data.item_key || `${gameId}:${itemId}`}`);
      } else {
        setStatusMessage(`❌ Error: ${data.detail || "Failed to publish item."}`);
      }
    } catch (err) {
      setStatusMessage("❌ Network error connecting to backend.");
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      <div className="max-w-4xl mx-auto space-y-8">
        
        <header className="flex justify-between items-center border-b border-slate-800 pb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-purple-400">DEVELOPER STUDIO PORTAL</h1>
            <p className="text-slate-400 text-sm">Authenticated Store Publishing & Economy Integration</p>
          </div>
          <Link href="/" className="bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-sm font-bold px-4 py-2 rounded-lg transition">
            ← Back to Player Portal
          </Link>
        </header>

        {!isAuthenticated ? (
          <div className="max-w-md mx-auto my-16 bg-slate-900 border border-purple-900/50 rounded-2xl p-8 space-y-6 text-center">
            <h2 className="text-xl font-bold text-purple-300">Developer Verification</h2>
            <p className="text-slate-400 text-sm">Enter your X-Developer-Key secret to unlock item publishing capabilities.</p>
            
            <form onSubmit={handleDevLogin} className="space-y-4">
              <input
                type="password"
                placeholder="X-Developer-Key Secret"
                value={developerKey}
                onChange={(e) => setDeveloperKey(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-sm text-slate-100 font-mono focus:outline-none focus:border-purple-500"
              />
              <button 
                type="submit" 
                className="w-full bg-purple-700 hover:bg-purple-600 text-white font-bold py-3 rounded-lg transition"
              >
                Authenticate Dev Studio
              </button>
            </form>

            {keyError && (
              <div className="bg-red-950/60 border border-red-800 text-red-300 px-4 py-3 rounded-lg text-xs font-mono text-left">
                {keyError}
              </div>
            )}
          </div>
        ) : (
          <div className="bg-slate-900 border border-purple-900/40 rounded-2xl p-8 space-y-6">
            <h2 className="text-xl font-bold text-slate-100">Publish New Game Cosmetic</h2>
            
            {statusMessage && (
              <div className="bg-purple-950/60 border border-purple-800 text-purple-300 px-4 py-3 rounded-lg text-sm font-mono">
                {statusMessage}
              </div>
            )}

            <form onSubmit={handlePublish} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-400 uppercase font-mono block mb-1">Game ID</label>
                  <input
                    type="text"
                    value={gameId}
                    onChange={(e) => setGameId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 uppercase font-mono block mb-1">Item ID</label>
                  <input
                    type="text"
                    placeholder="skin_cyber_01"
                    value={itemId}
                    onChange={(e) => setItemId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm font-mono"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-400 uppercase font-mono block mb-1">Price (NEX)</label>
                  <input
                    type="number"
                    value={priceNex}
                    onChange={(e) => setPriceNex(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 uppercase font-mono block mb-1">Category</label>
                  <input
                    type="text"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm font-mono"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 uppercase font-mono block mb-1">Display Name</label>
                <input
                  type="text"
                  placeholder="Neon Mech Armor"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm font-mono"
                  required
                />
              </div>

              <button
                type="submit"
                className="w-full bg-purple-600 hover:bg-purple-500 text-white font-bold py-3 rounded-lg transition"
              >
                Publish Cosmetic (13% Burn Sink)
              </button>
            </form>
          </div>
        )}

      </div>
    </main>
  );
}