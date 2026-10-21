const BASE_URL = "https://main-coin-backend.onrender.com";

export interface PlayerProfile {
  player_id: string;
  spendable_nex: number;
  total_nex_earned: number;
  total_hours_played: number;
  prestige_level: number;
  nametag_style: {
    text_color: string;
    emblem_icon: string | null;
    display_name_formatted: string;
  };
}

export interface StoreCatalog {
  global_cosmetics: Array<{
    item_id: string;
    name: string;
    description: string;
    price_nex: number;
  }>;
  developer_cosmetics: Array<{
    item_key: string;
    game_id: string;
    name: string;
    price_nex: number;
    category: string;
    asset_url: string;
  }>;
}

export async function fetchPlayerProfile(playerId: string): Promise<PlayerProfile> {
  const res = await fetch(`${BASE_URL}/api/v1/player/${playerId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch profile");
  return res.json();
}

export async function fetchStoreCatalog(): Promise<StoreCatalog> {
  const res = await fetch(`${BASE_URL}/api/v1/store/catalogue`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch catalogue");
  return res.json();
}

export async function registerGame(developerId: string, gameName: string, webhookUrl: string) {
  const res = await fetch(`${BASE_URL}/api/v1/developer/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      developer_id: developerId,
      game_name: gameName,
      webhook_url: webhookUrl,
    }),
  });
  return res.json();
}