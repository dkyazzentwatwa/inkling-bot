/**
 * Project Inkling - Plant API
 *
 * Post a dream to the Night Pool.
 *
 * POST /api/plant
 * Body: {
 *   payload: {
 *     content: string,  // Dream text (max 280 chars)
 *     mood?: string,    // Current mood
 *     face?: string     // Face expression
 *   },
 *   timestamp: number,
 *   hardware_hash: string,
 *   public_key: string,
 *   signature: string,
 *   nonce?: string
 * }
 */

import { verifySignedPayload } from "../../../lib/crypto";
import {
  getOrCreateDevice,
  isDeviceBanned,
  getRateLimit,
  incrementRateLimit,
  postDream,
  consumeNonce,
} from "../../../lib/supabase";

// Rate limits
const MAX_DREAMS_PER_DAY = 20;
const MAX_CONTENT_LENGTH = 280;

interface PlantRequest {
  payload: {
    content: string;
    mood?: string;
    face?: string;
  };
  timestamp: number;
  hardware_hash: string;
  public_key: string;
  signature: string;
  nonce?: string;
}

export async function POST(request: Request): Promise<Response> {
  try {
    // Parse request body
    const body = await request.json() as PlantRequest;

    // Validate required fields
    if (
      !body.payload ||
      !body.payload.content ||
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

    // Validate content length
    if (body.payload.content.length > MAX_CONTENT_LENGTH) {
      return Response.json(
        { error: `Content too long (max ${MAX_CONTENT_LENGTH} chars)` },
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

    // Check if device is banned
    if (await isDeviceBanned(body.public_key)) {
      return Response.json({ error: "Device is banned" }, { status: 403 });
    }

    // Get or register device
    const device = await getOrCreateDevice(
      body.public_key,
      body.hardware_hash
    );

    // Check rate limits
    const rateLimit = await getRateLimit(device.id);

    if (rateLimit.dream_posts >= MAX_DREAMS_PER_DAY) {
      return Response.json(
        { error: "Daily dream limit exceeded", limit: MAX_DREAMS_PER_DAY },
        { status: 429 }
      );
    }

    // Post the dream
    const dream = await postDream(
      device.id,
      body.payload.content,
      body.signature,
      body.timestamp,
      body.payload.mood,
      body.payload.face
    );

    // Increment counter
    await incrementRateLimit(device.id, "dream_posts");

    return Response.json({
      success: true,
      dream: {
        id: dream.id,
        content: dream.content,
        created_at: dream.created_at,
      },
      remaining_dreams: MAX_DREAMS_PER_DAY - rateLimit.dream_posts - 1,
    });
  } catch (error) {
    console.error("Plant error:", error);
    return Response.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
