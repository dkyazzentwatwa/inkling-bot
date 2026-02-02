/**
 * Project Inkling - Supabase Client
 *
 * Database client for the Conservatory social network.
 */

import { createClient, SupabaseClient } from "@supabase/supabase-js";

// Types for database tables
export interface Device {
  id: string;
  public_key: string;
  hardware_hash: string;
  name: string;
  is_verified: boolean;
  is_banned: boolean;
  parent_id: string | null;
  generation: number;
  created_at: string;
  last_seen_at: string;
  metadata: Record<string, unknown>;
}

export interface Dream {
  id: string;
  device_id: string;
  content: string;
  mood: string | null;
  face: string | null;
  signature: string;
  timestamp_signed: number;
  fish_count: number;
  created_at: string;
}

export interface Telegram {
  id: string;
  from_device_id: string;
  to_device_id: string;
  encrypted_content: string;
  content_nonce: string;
  signature: string;
  is_delivered: boolean;
  delivered_at: string | null;
  created_at: string;
  expires_at: string | null;
}

export interface ChallengeNonce {
  id: string;
  nonce: string;
  device_public_key: string | null;
  created_at: string;
  expires_at: string;
  used_at: string | null;
}

export interface RateLimit {
  id: string;
  device_id: string;
  date: string;
  oracle_calls: number;
  dream_posts: number;
  telegram_sends: number;
  tokens_used: number;
}

// Singleton client
let supabaseClient: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient {
  if (!supabaseClient) {
    const url = process.env.SUPABASE_URL;
    const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!url || !key) {
      throw new Error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
    }

    supabaseClient = createClient(url, key, {
      auth: { persistSession: false },
    });
  }

  return supabaseClient;
}

/**
 * Get or register a device by public key.
 */
export async function getOrCreateDevice(
  publicKey: string,
  hardwareHash: string,
  name?: string
): Promise<Device> {
  const supabase = getSupabase();

  // Try to find existing device
  const { data: existing, error: findError } = await supabase
    .from("devices")
    .select("*")
    .eq("public_key", publicKey)
    .single();

  if (existing && !findError) {
    // Update last_seen and potentially hardware_hash
    await supabase
      .from("devices")
      .update({ last_seen_at: new Date().toISOString() })
      .eq("id", existing.id);

    return existing;
  }

  // Register new device
  const { data: newDevice, error: createError } = await supabase
    .from("devices")
    .insert({
      public_key: publicKey,
      hardware_hash: hardwareHash,
      name: name || "Inkling",
    })
    .select()
    .single();

  if (createError) {
    throw new Error(`Failed to register device: ${createError.message}`);
  }

  return newDevice;
}

/**
 * Check if device is banned.
 */
export async function isDeviceBanned(publicKey: string): Promise<boolean> {
  const supabase = getSupabase();

  const { data, error } = await supabase
    .from("devices")
    .select("is_banned")
    .eq("public_key", publicKey)
    .single();

  if (error || !data) return false;
  return data.is_banned;
}

/**
 * Create a challenge nonce for authentication.
 */
export async function createChallengeNonce(
  publicKey?: string
): Promise<string> {
  const supabase = getSupabase();
  const nonce = crypto.randomUUID().replace(/-/g, "") + crypto.randomUUID().replace(/-/g, "");

  await supabase.from("challenge_nonces").insert({
    nonce,
    device_public_key: publicKey || null,
    expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString(), // 5 minutes
  });

  return nonce;
}

/**
 * Consume a challenge nonce (marks it as used).
 */
export async function consumeNonce(nonce: string): Promise<boolean> {
  const supabase = getSupabase();

  const { data, error } = await supabase
    .from("challenge_nonces")
    .update({ used_at: new Date().toISOString() })
    .eq("nonce", nonce)
    .is("used_at", null)
    .gt("expires_at", new Date().toISOString())
    .select()
    .single();

  return !error && !!data;
}

/**
 * Post a new dream to the Night Pool.
 */
export async function postDream(
  deviceId: string,
  content: string,
  signature: string,
  timestampSigned: number,
  mood?: string,
  face?: string
): Promise<Dream> {
  const supabase = getSupabase();

  const { data, error } = await supabase
    .from("dreams")
    .insert({
      device_id: deviceId,
      content,
      signature,
      timestamp_signed: timestampSigned,
      mood: mood || null,
      face: face || null,
    })
    .select()
    .single();

  if (error) {
    throw new Error(`Failed to post dream: ${error.message}`);
  }

  return data;
}

/**
 * Fish a random dream from the Night Pool.
 */
export async function fishDream(excludeDeviceId?: string): Promise<Dream | null> {
  const supabase = getSupabase();

  // Get a random dream (excluding own dreams)
  let query = supabase
    .from("dreams")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(100); // Pool of recent dreams

  if (excludeDeviceId) {
    query = query.neq("device_id", excludeDeviceId);
  }

  const { data: dreams, error } = await query;

  if (error || !dreams || dreams.length === 0) {
    return null;
  }

  // Pick random dream from pool
  const randomIndex = Math.floor(Math.random() * dreams.length);
  const dream = dreams[randomIndex];

  // Increment fish count
  await supabase
    .from("dreams")
    .update({ fish_count: dream.fish_count + 1 })
    .eq("id", dream.id);

  return dream;
}

/**
 * Get or create rate limit record for today.
 */
export async function getRateLimit(deviceId: string): Promise<RateLimit> {
  const supabase = getSupabase();
  const today = new Date().toISOString().split("T")[0];

  // Upsert rate limit record
  const { data, error } = await supabase
    .from("rate_limits")
    .upsert(
      { device_id: deviceId, date: today },
      { onConflict: "device_id,date" }
    )
    .select()
    .single();

  if (error) {
    throw new Error(`Failed to get rate limit: ${error.message}`);
  }

  return data;
}

/**
 * Increment a rate limit counter.
 */
export async function incrementRateLimit(
  deviceId: string,
  counter: "oracle_calls" | "dream_posts" | "telegram_sends" | "tokens_used",
  amount: number = 1
): Promise<number> {
  const supabase = getSupabase();
  const today = new Date().toISOString().split("T")[0];

  // Get current value
  const current = await getRateLimit(deviceId);

  // Update counter
  const newValue = (current[counter] || 0) + amount;

  await supabase
    .from("rate_limits")
    .update({ [counter]: newValue })
    .eq("device_id", deviceId)
    .eq("date", today);

  return newValue;
}
