"use client";

import { useState } from "react";
import Link from "next/link";

const BASE_URL = "https://main-coin-backend.onrender.com";
const DEV_KEY = "nexus_dev_secret_2026";

export default function DeveloperStudio() {
  // Developer Registration State
  const [developerId, setDeveloperId] = useState("");
  const [gameName, setGameName] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [regStatus, setRegStatus] = useState<string | null>(null);

  // Cosmetic Publishing State
  const [gameId, setGameId] = useState("game_palworld_mech_arena");
  const [itemId, setItemId] = useState("skin_cyber_01");
  const [priceNex, setPriceNex] = useState("100");
  const [category, setCategory] = useState("Skin");
  const [displayName, setDisplayName] = useState("Neon Mech Armor");
  const [pubStatus, setPubStatus] = useState<string | null>(null);

  // 1. Handle Game Registration
  const handleRegisterGame = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegStatus("Registering game...");
    try {
      const res = await fetch(`${BASE_URL}/api/v1/developer/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Developer-Key": DEV_KEY,
        },
        body: JSON.stringify({
          developer_id: developerId,
          game_name: gameName,
          webhook_url: webhookUrl || null,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setRegStatus(`✅ Registered! Assigned Game ID: ${data.game_id}`);
        setGameId(data.game_id); // Auto-fill the published cosmetic form with the new Game ID
      } else {
        setRegStatus(`❌ Registration failed: ${data.detail || "Error"}`);
      }
    } catch (err) {
      setRegStatus("❌ Network error connecting to backend.");
    }
  };

  // 2. Handle Cosmetic Publishing
  const handlePublishCosmetic = async (e: React.FormEvent) => {
    e.preventDefault();
    setPubStatus("Publishing item...");
    try {
      const res = await fetch(`${BASE_URL}/api/v1/developer/cosmetics/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Developer-Key": DEV_KEY,
        },
        body: JSON.stringify({
          game_id: gameId,
          item_id: itemId,
          item_name: displayName,
          price_nex: parseFloat(priceNex),
          category: category,
          asset_url: "https://cdn.nexus.io/assets/cosmetic.png",
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setPubStatus(`✅ Published! Item Key: ${data.item_key}`);
      } else {
        setPubStatus(`❌ Failed to publish: ${data.detail || "Game ID not registered"}`);
      }
    } catch (err) {
      setPubStatus("❌ Network error connecting to backend.");
    }
  };

  return (
    <div className="min-h-screen bg-[#0b0e14] text-white p-8 font-sans">
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-500">
              DEVELOPER STUDIO PORTAL
            </h1>
            <p className="text-gray-400 text-sm">Authenticated Store Publishing & Economy Integration</p>
          </div>
          <Link href="/" className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm border border-gray-700 transition">
            ← Back to Player Portal
          </Link>
        </div>

        {/* SECTION 1: Register Game Studio */}
        <div className="bg-[#131722] border border-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="text-xl font-bold text-purple-400">1. Register Game Studio Title</h2>
          <form onSubmit={handleRegisterGame} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono text-gray-400 mb-1">DEVELOPER ID</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. dev_studio_alpha"
                  value={developerId}
                  onChange={(e) => setDeveloperId(e.target.value)}
                  className="w-full bg-[#0b0e14] border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-purple-500"
                />
              </div>
              <div>
                <label className="block text-xs font-mono text-gray-400 mb-1">GAME NAME</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Palworld Mech Arena"
                  value={gameName}
                  onChange={(e) => setGameName(e.target.value)}
                  className="w-full bg-[#0b0e14] border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-mono text-gray-400 mb-1">WEBHOOK URL (OPTIONAL)</label>
              <input
                type="text"
                placeholder="https://api.yourstudio.com/nexus/webhooks"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="w-full bg-[#0b0e14] border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-purple-500"
              />
            </div>
            <button
              type="submit"
              className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 font-bold py-2.5 rounded-lg transition"
            >
              Register Studio Title
            </button>
            {regStatus && <p className="text-sm font-mono text-center text-cyan-400 mt-2">{regStatus}</p>}
          </form>
        </div>

        {/* SECTION 2: Publish Cosmetic */}
        <div className="bg-[#131722] border border-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="text-xl font-bold text-purple-400">2. Publish New Game Cosmetic</h2>
          <form onSubmit={handlePublishCosmetic} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono text-gray-400 mb-1">GAME ID</label>
                <input
                  type="text"
                  required
                  value={gameId}
                  onChange={(e) => setGameId(e.target.value)}
                  className="w-full bg-[#0b0e14] border border-gray-700 rounded p-2 text-sm text-white font-mono focus:outline-none focus:border-purple-500"
                />
              </div>
              <div>
                <label className="block text-xs font-mono text-gray-400 mb-1">ITEM ID</label>
                <input
                  type="text"
                  required
                  value={itemId}
                  onChange={(e) => setItemId(e.target.value)}
                  className="w-full bg-[#0b0e14] border border-gray-700 rounded p-2 text-sm text-white font-mono focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono text-gray-400 mb-1">PRICE (NEX)</label>
                <input
                  type="number"
                  required
                  value={priceNex}
                  onChange={(e) => setPriceNex(e.target.value)}
                  className="w-full bg-[#0b0e14] border border-gray-700 rounded p-2 text-sm text-white font-mono focus:outline-none focus:border-purple-500"
                />
              </div>
              <div>
                <label className="block text-xs font-mono text-gray-400 mb-1">CATEGORY</label>
                <input
                  type="text"
                  required
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-[#0b0e14] border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono text-gray-400 mb-1">DISPLAY NAME</label>
              <input
                type="text"
                required
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full bg-[#0b0e14] border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            <button
              type="submit"
              className="w-full bg-purple-600 hover:bg-purple-500 text-white font-bold py-3 rounded-lg transition"
            >
              Publish Cosmetic (13% Burn Sink)
            </button>
            {pubStatus && <p className="text-sm font-mono text-center text-cyan-400 mt-2">{pubStatus}</p>}
          </form>
        </div>

      </div>
    </div>
  );
}