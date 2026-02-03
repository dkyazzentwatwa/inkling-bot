/**
 * Project Inkling - Fish API
 *
 * Retrieve a random dream from the Night Pool.
 *
 * POST /api/fish
 * Body: {
 *   payload: {},  // Empty payload, just need auth
 *   timestamp: number,
 *   hardware_hash: string,
 *   public_key: string,
 *   signature: string,
 *   nonce?: string
 * }
 *
 * GET /api/fish
 * Public endpoint - returns a random dream without auth
 * (for the Night Pool web viewer)
 */

import { verifySignedPayload } from "../../../lib/crypto";
import {
  getOrCreateDevice,
  isDeviceBanned,
  fishDream,
  consumeNonce,
  type Dream,
} from "../../../lib/supabase";

interface FishRequest {
  payload: Record<string, unknown>;
  timestamp: number;
  hardware_hash: string;
  public_key: string;
  signature: string;
  nonce?: string;
}

// Authenticated fishing (from device)
export async function POST(request: Request): Promise<Response> {
  try {
    // Parse request body
    const body = await request.json() as FishRequest;

    // Validate required fields
    if (
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
      payload: body.payload || {},
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

    // Check if device is banned
    if (await isDeviceBanned(body.public_key)) {
      return Response.json({ error: "Device is banned" }, { status: 403 });
    }

    // Get or register device
    const device = await getOrCreateDevice(
      body.public_key,
      body.hardware_hash
    );

    // Fish a dream (excluding own dreams)
    const dream = await fishDream(device.id);

    if (!dream) {
      return Response.json({
        success: true,
        dream: null,
        message: "The Night Pool is empty",
      });
    }

    return Response.json({
      success: true,
      dream: formatDreamResponse(dream),
    });
  } catch (error) {
    console.error("Fish error:", error);
    return Response.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// Public fishing (for Night Pool web viewer)
export async function GET(): Promise<Response> {
  try {
    // Fish a random dream (no exclusions for public viewing)
    const dream = await fishDream();

    if (!dream) {
      return Response.json({
        success: true,
        dream: null,
        message: "The Night Pool is empty",
      });
    }

    return Response.json({
      success: true,
      dream: formatDreamResponse(dream),
    });
  } catch (error) {
    console.error("Fish error:", error);
    return Response.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

function formatDreamResponse(dream: Dream) {
  return {
    id: dream.id,
    content: dream.content,
    mood: dream.mood,
    face: dream.face,
    fish_count: dream.fish_count,
    created_at: dream.created_at,
    // Don't expose device_id or signature to clients
  };
}
