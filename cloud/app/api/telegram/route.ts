/**
 * Project Inkling - Telegram API
 *
 * Encrypted direct messages between devices.
 *
 * POST /api/telegram - Send a telegram
 * GET /api/telegram - Get inbox (pending telegrams)
 */

import { verifySignedPayload } from "../../../lib/crypto";
import {
  getOrCreateDevice,
  isDeviceBanned,
  getRateLimit,
  incrementRateLimit,
  consumeNonce,
  getSupabase,
  type Telegram,
} from "../../../lib/supabase";

// Rate limits
const MAX_TELEGRAMS_PER_DAY = 50;

interface SendTelegramRequest {
  payload: {
    to_public_key: string;      // Recipient's Ed25519 public key
    encrypted_content: string;   // Base64 encrypted message
    content_nonce: string;       // Encryption nonce (hex)
    sender_encryption_key: string; // Sender's X25519 public key
  };
  timestamp: number;
  hardware_hash: string;
  public_key: string;
  signature: string;
  nonce?: string;
}

// POST - Send a telegram
export async function POST(request: Request): Promise<Response> {
  try {
    const body: SendTelegramRequest = await request.json();

    // Validate required fields
    if (
      !body.payload?.to_public_key ||
      !body.payload?.encrypted_content ||
      !body.payload?.content_nonce ||
      !body.payload?.sender_encryption_key ||
      !body.timestamp ||
      !body.hardware_hash ||
      !body.public_key ||
      !body.signature
    ) {
      return Response.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    // Verify signature
    const verification = await verifySignedPayload({
      payload: body.payload,
      timestamp: body.timestamp,
      hardware_hash: body.hardware_hash,
      public_key: body.public_key,
      signature: body.signature,
      nonce: body.nonce,
    });

    if (!verification.valid) {
      return Response.json(
        { error: verification.error || "Invalid signature" },
        { status: 401 }
      );
    }

    // Consume nonce if provided
    if (body.nonce) {
      const nonceValid = await consumeNonce(body.nonce);
      if (!nonceValid) {
        return Response.json(
          { error: "Invalid or expired nonce" },
          { status: 401 }
        );
      }
    }

    // Check if sender is banned
    if (await isDeviceBanned(body.public_key)) {
      return Response.json({ error: "Device is banned" }, { status: 403 });
    }

    // Get sender device
    const sender = await getOrCreateDevice(body.public_key, body.hardware_hash);

    // Check rate limits
    const rateLimit = await getRateLimit(sender.id);
    if (rateLimit.telegram_sends >= MAX_TELEGRAMS_PER_DAY) {
      return Response.json(
        { error: "Daily telegram limit exceeded", limit: MAX_TELEGRAMS_PER_DAY },
        { status: 429 }
      );
    }

    // Find recipient by public key
    const supabase = getSupabase();
    const { data: recipient, error: recipientError } = await supabase
      .from("devices")
      .select("id, public_key")
      .eq("public_key", body.payload.to_public_key)
      .single();

    if (recipientError || !recipient) {
      return Response.json(
        { error: "Recipient not found" },
        { status: 404 }
      );
    }

    // Can't send to yourself
    if (recipient.id === sender.id) {
      return Response.json(
        { error: "Cannot send telegram to yourself" },
        { status: 400 }
      );
    }

    // Store the telegram
    const { data: telegram, error: insertError } = await supabase
      .from("telegrams")
      .insert({
        from_device_id: sender.id,
        to_device_id: recipient.id,
        encrypted_content: body.payload.encrypted_content,
        content_nonce: body.payload.content_nonce,
        signature: body.signature,
        // Store sender's encryption key in metadata for decryption
        // (The schema doesn't have this field, so we'll need to add it or use a workaround)
      })
      .select()
      .single();

    if (insertError) {
      console.error("Failed to store telegram:", insertError);
      return Response.json(
        { error: "Failed to send telegram" },
        { status: 500 }
      );
    }

    // Increment rate limit
    await incrementRateLimit(sender.id, "telegram_sends");

    return Response.json({
      success: true,
      telegram_id: telegram.id,
      remaining_telegrams: MAX_TELEGRAMS_PER_DAY - rateLimit.telegram_sends - 1,
    });
  } catch (error) {
    console.error("Telegram send error:", error);
    return Response.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// GET - Fetch inbox
export async function GET(request: Request): Promise<Response> {
  try {
    // Get device info from query params (simplified auth for inbox check)
    const url = new URL(request.url);
    const publicKey = url.searchParams.get("public_key");
    const signature = url.searchParams.get("signature");
    const timestamp = url.searchParams.get("timestamp");

    if (!publicKey) {
      return Response.json(
        { error: "Missing public_key parameter" },
        { status: 400 }
      );
    }

    // For inbox, we do a simplified check - just verify the device exists
    const supabase = getSupabase();
    const { data: device, error: deviceError } = await supabase
      .from("devices")
      .select("id")
      .eq("public_key", publicKey)
      .single();

    if (deviceError || !device) {
      return Response.json(
        { error: "Device not found" },
        { status: 404 }
      );
    }

    // Fetch undelivered telegrams
    const { data: telegrams, error: fetchError } = await supabase
      .from("telegrams")
      .select(`
        id,
        from_device_id,
        encrypted_content,
        content_nonce,
        created_at,
        is_delivered
      `)
      .eq("to_device_id", device.id)
      .eq("is_delivered", false)
      .order("created_at", { ascending: true })
      .limit(20);

    if (fetchError) {
      console.error("Failed to fetch telegrams:", fetchError);
      return Response.json(
        { error: "Failed to fetch inbox" },
        { status: 500 }
      );
    }

    // Get sender info for each telegram
    const telegramIds = telegrams.map((t) => t.id);
    const senderIds = [...new Set(telegrams.map((t) => t.from_device_id))];

    const { data: senders } = await supabase
      .from("devices")
      .select("id, public_key, name")
      .in("id", senderIds);

    const senderMap = new Map(senders?.map((s) => [s.id, s]) || []);

    // Format response
    const formattedTelegrams = telegrams.map((t) => {
      const sender = senderMap.get(t.from_device_id);
      return {
        id: t.id,
        from_device_id: t.from_device_id,
        from_name: sender?.name || "Unknown",
        encrypted_content: t.encrypted_content,
        content_nonce: t.content_nonce,
        sender_encryption_key: "", // TODO: Store and return this
        created_at: t.created_at,
        is_delivered: t.is_delivered,
      };
    });

    // Mark as delivered
    if (telegramIds.length > 0) {
      await supabase
        .from("telegrams")
        .update({
          is_delivered: true,
          delivered_at: new Date().toISOString(),
        })
        .in("id", telegramIds);
    }

    return Response.json({
      success: true,
      telegrams: formattedTelegrams,
      count: formattedTelegrams.length,
    });
  } catch (error) {
    console.error("Telegram inbox error:", error);
    return Response.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
