/**
 * Project Inkling - Postcard API
 *
 * Send and receive 1-bit pixel art postcards.
 *
 * POST /api/postcard - Send a postcard
 * GET /api/postcard - Get postcards for device
 * GET /api/postcard?public=true - Get public postcards
 */

import { verifySignedPayload } from "../../../lib/crypto";
import {
  getOrCreateDevice,
  isDeviceBanned,
  getRateLimit,
  incrementRateLimit,
  consumeNonce,
  getSupabase,
} from "../../../lib/supabase";

// Rate limits
const MAX_POSTCARDS_PER_DAY = 10;
const MAX_IMAGE_SIZE = 10000; // Base64 characters

interface SendPostcardRequest {
  payload: {
    image_data: string;      // Base64 compressed bitmap
    width: number;
    height: number;
    caption?: string;        // Optional caption (max 60 chars)
    to_public_key?: string;  // Recipient (null = public)
  };
  timestamp: number;
  hardware_hash: string;
  public_key: string;
  signature: string;
  nonce?: string;
}

// POST - Send a postcard
export async function POST(request: Request): Promise<Response> {
  try {
    const body: SendPostcardRequest = await request.json();

    // Validate required fields
    if (
      !body.payload?.image_data ||
      !body.payload?.width ||
      !body.payload?.height ||
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

    // Validate image data size
    if (body.payload.image_data.length > MAX_IMAGE_SIZE) {
      return Response.json(
        { error: `Image data too large (max ${MAX_IMAGE_SIZE} chars)` },
        { status: 400 }
      );
    }

    // Validate dimensions
    if (
      body.payload.width <= 0 || body.payload.width > 250 ||
      body.payload.height <= 0 || body.payload.height > 122
    ) {
      return Response.json(
        { error: "Invalid dimensions (max 250x122)" },
        { status: 400 }
      );
    }

    // Validate caption
    if (body.payload.caption && body.payload.caption.length > 60) {
      return Response.json(
        { error: "Caption too long (max 60 chars)" },
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
    const supabase = getSupabase();
    const today = new Date().toISOString().split("T")[0];

    // Count postcards sent today
    const { count } = await supabase
      .from("postcards")
      .select("*", { count: "exact", head: true })
      .eq("from_device_id", sender.id)
      .gte("created_at", `${today}T00:00:00Z`);

    if ((count || 0) >= MAX_POSTCARDS_PER_DAY) {
      return Response.json(
        { error: "Daily postcard limit exceeded", limit: MAX_POSTCARDS_PER_DAY },
        { status: 429 }
      );
    }

    // Find recipient if specified
    let toDeviceId = null;
    if (body.payload.to_public_key) {
      const { data: recipient } = await supabase
        .from("devices")
        .select("id")
        .eq("public_key", body.payload.to_public_key)
        .single();

      if (!recipient) {
        return Response.json(
          { error: "Recipient not found" },
          { status: 404 }
        );
      }
      toDeviceId = recipient.id;
    }

    // Store postcard
    const { data: postcard, error: insertError } = await supabase
      .from("postcards")
      .insert({
        from_device_id: sender.id,
        to_device_id: toDeviceId,
        image_data: body.payload.image_data,
        width: body.payload.width,
        height: body.payload.height,
        caption: body.payload.caption || null,
        signature: body.signature,
      })
      .select()
      .single();

    if (insertError) {
      console.error("Failed to store postcard:", insertError);
      return Response.json(
        { error: "Failed to send postcard" },
        { status: 500 }
      );
    }

    return Response.json({
      success: true,
      postcard_id: postcard.id,
      remaining_postcards: MAX_POSTCARDS_PER_DAY - (count || 0) - 1,
    });
  } catch (error) {
    console.error("Postcard send error:", error);
    return Response.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// GET - Fetch postcards
export async function GET(request: Request): Promise<Response> {
  try {
    const url = new URL(request.url);
    const publicKey = url.searchParams.get("public_key");
    const isPublic = url.searchParams.get("public") === "true";

    const supabase = getSupabase();

    if (isPublic) {
      // Get public postcards (no recipient)
      const { data: postcards, error } = await supabase
        .from("postcards")
        .select(`
          id,
          image_data,
          width,
          height,
          caption,
          created_at,
          from_device_id
        `)
        .is("to_device_id", null)
        .order("created_at", { ascending: false })
        .limit(20);

      if (error) {
        return Response.json(
          { error: "Failed to fetch postcards" },
          { status: 500 }
        );
      }

      // Get sender names
      const senderIds = [...new Set(postcards.map((p) => p.from_device_id))];
      const { data: senders } = await supabase
        .from("devices")
        .select("id, name")
        .in("id", senderIds);

      const senderMap = new Map(senders?.map((s) => [s.id, s.name]) || []);

      const formatted = postcards.map((p) => ({
        id: p.id,
        image_data: p.image_data,
        width: p.width,
        height: p.height,
        caption: p.caption,
        from_name: senderMap.get(p.from_device_id) || "Unknown",
        created_at: p.created_at,
      }));

      return Response.json({
        success: true,
        postcards: formatted,
        count: formatted.length,
      });
    }

    // Get postcards for specific device
    if (!publicKey) {
      return Response.json(
        { error: "Missing public_key parameter" },
        { status: 400 }
      );
    }

    // Find device
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

    // Get postcards sent to this device
    const { data: postcards, error } = await supabase
      .from("postcards")
      .select(`
        id,
        image_data,
        width,
        height,
        caption,
        created_at,
        from_device_id
      `)
      .eq("to_device_id", device.id)
      .order("created_at", { ascending: false })
      .limit(20);

    if (error) {
      return Response.json(
        { error: "Failed to fetch postcards" },
        { status: 500 }
      );
    }

    // Get sender names
    const senderIds = [...new Set(postcards.map((p) => p.from_device_id))];
    const { data: senders } = await supabase
      .from("devices")
      .select("id, name")
      .in("id", senderIds);

    const senderMap = new Map(senders?.map((s) => [s.id, s.name]) || []);

    const formatted = postcards.map((p) => ({
      id: p.id,
      image_data: p.image_data,
      width: p.width,
      height: p.height,
      caption: p.caption,
      from_name: senderMap.get(p.from_device_id) || "Unknown",
      created_at: p.created_at,
    }));

    return Response.json({
      success: true,
      postcards: formatted,
      count: formatted.length,
    });
  } catch (error) {
    console.error("Postcard fetch error:", error);
    return Response.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
