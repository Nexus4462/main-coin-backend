"use client";

import { useState } from "react";
import Link from "next/link";
import { registerGame } from "@/lib/api";

export default function DeveloperPortal() {
  const [devSecretKey, setDevSecretKey] = useState("");

  // Game Registration State
  const [devId, setDevId] = useState("");
  const [gameName, setGameName] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [regStatus, setRegStatus] = useState<string | null>(null);

  // Cosmetic Creation State
  const [cosmeticGameId, setCosmeticGameId] = useState("");
  const [itemId, setItemId] = useState("");
  const [itemName, setItemName] = useState("");
  const [price, setPrice] = useState("");
  const [category, setCategory] = useState("skin");
  const [cosmeticStatus, setCosmeticStatus] = useState<string | null>(null);

  const handleRegisterGame = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegStatus("Registering...");
    try {
      const res = await registerGame(devId, gameName, webhookUrl);
      if (res.status === "SUCCESS") {
        setRegStatus(`✅ Registered successfully! Game ID: ${res.game_id}`);
        setCosmeticGameId(res.game_id);
      } else {
        setRegStatus(`❌ Error: ${res.detail || "Registration failed"}`);
      }
    } catch (err) {
      setRegStatus("❌ Network error connecting to Render backend.");
    }
  };

  const handleAddCosmetic = async (e: React.FormEvent) => {
    e.preventDefault();
    setCosmeticStatus("Publishing cosmetic...");
    try {
      const res = await fetch("https://main-coin-backend.onrender.com/api/v1/developer/cosmetics/add", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "X-Developer-Key": devSecretKey
        },
        body: JSON.stringify({
          game_id: cosmeticGameId,
          item_id: itemId,
          item_name: itemName,
          price_nex: parseFloat(price),
          asset_url: "https://example.com/assets/default.png",
          category: category,
        }),
      });
      const data = await res.json();
      if (data.status === "SUCCESS") {
        setCosmeticStatus(`✅ Published! Key: ${data.item_key}`);
      } else {
        setCosmeticStatus(`❌ Error: ${data.detail || "Failed to publish"}`);
      }
    } catch (err) {
      setCosmeticStatus("❌ Network error connecting to Render backend.");
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* Header Navigation */}
        <header className="flex justify-between items-center border-b border-slate-800 pb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-purple-400">DEVELOPER STUDIO PORTAL</h1>
            <p className="text-slate-400 text-sm">Register Third-Party Games & Publish In-Game Cosmetics</p>
          </div>
          <Link href="/" className="bg-slate-900 hover:bg-slate-800 border border-slate-700 text-cyan-400 text-sm font-bold px-4 py-2 rounded-lg transition">
            ← Back to Dashboard
          </Link>
        </header>

        {/* Grid Forms */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* Form 1: Register Game */}
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl space-y-4">
            <h2 className="text-xl font-bold text-slate-200">1. Register Game Title</h2>
            <form onSubmit={handleRegisterGame} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Developer / Studio ID</label>
                <input
                  type="text"
                  placeholder="e.g. dev_salina_01"
                  value={devId}
                  onChange={(e) => setDevId(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Game Title</label>
                <input
                  type="text"
                  placeholder="e.g. Palworld Mech Arena"
                  value={gameName}
                  onChange={(e) => setGameName(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Webhook URL</label>
                <input
                  type="url"
                  placeholder="https://example.com/webhook"
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-purple-600 hover:bg-purple-500 text-white font-bold py-2 rounded transition text-sm"
              >
                Register Game
              </button>
            </form>
            {regStatus && <p className="text-xs font-mono mt-2 text-purple-300">{regStatus}</p>}
          </div>

          {/* Form 2: Publish Cosmetic */}
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl space-y-4">
            <h2 className="text-xl font-bold text-slate-200">2. Add Game Cosmetic</h2>
            <form onSubmit={handleAddCosmetic} className="space-y-4">
              
              {/* Developer Secret Key */}
              <div>
                <label className="block text-xs font-mono text-purple-400 mb-1">Developer Secret Key</label>
                <input
                  type="password"
                  placeholder="Enter dev secret key"
                  value={devSecretKey}
                  onChange={(e) => setDevSecretKey(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-purple-900/60 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              {/* Game ID */}
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Game ID</label>
                <input
                  type="text"
                  placeholder="e.g. game_palworld_mech_arena"
                  value={cosmeticGameId}
                  onChange={(e) => setCosmeticGameId(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Item ID</label>
                <input
                  type="text"
                  placeholder="e.g. legendary_sword"
                  value={itemId}
                  onChange={(e) => setItemId(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Item Name</label>
                <input
                  type="text"
                  placeholder="e.g. Legendary Sword"
                  value={itemName}
                  onChange={(e) => setItemName(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Price (NEX)</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  placeholder="e.g. 100"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-purple-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-purple-500 font-mono"
                >
                  <option value="skin">Skin</option>
                  <option value="weapon">Weapon</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <button
                type="submit"
                className="w-full bg-purple-600 hover:bg-purple-500 text-white font-bold py-2 rounded transition text-sm"
              >
                Publish Cosmetic
              </button>
            </form>
            {cosmeticStatus && <p className="text-xs font-mono mt-2 text-purple-300">{cosmeticStatus}</p>}
          </div>
        </div>
      </div>
    </main>
  );
}