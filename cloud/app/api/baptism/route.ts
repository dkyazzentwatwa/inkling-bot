/**
 * Project Inkling - Baptism API
 *
 * Web-of-trust device verification system.
 *
 * POST /api/baptism/request - Request baptism
 * POST /api/baptism/endorse - Endorse a device
 * GET /api/baptism/status?public_key=X - Get baptism status
 * GET /api/baptism/pending - Get pending baptism requests
 */

import { verifySignedPayload } from "../../../lib/crypto";
import {
  getOrCreateDevice,
  isDeviceBanned,
  getSupabase,
} from "../../../lib/supabase";

// Trust thresholds
const MIN_ENDORSEMENTS = 2;
const TRUST_THRESHOLD = 3.0;

interface BaptismRequestBody {
  payload: {
    action: "request" | "endorse" | "revoke";
    message?: string;
    target_public_key?: string;  // For endorsement
  };
  timestamp: number;
  hardware_hash: string;
  public_key: string;
  signature: string;
  nonce?: string;
}

export async function POST(request: Request): Promise<Response> {
  try {
    const body: BaptismRequestBody = await request.json();

    // Validate
    if (!body.payload?.action || !body.public_key || !body.signature) {
      return Response.json({ error: "Missing required fields" }, { status: 400 });
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

    // Check if banned
    if (await isDeviceBanned(body.public_key)) {
      return Response.json({ error: "Device is banned" }, { status: 403 });
    }

    const supabase = getSupabase();
    const device = await getOrCreateDevice(body.public_key, body.hardware_hash);

    switch (body.payload.action) {
      case "request":
        return await handleBaptismRequest(supabase, device, body);

      case "endorse":
        return await handleEndorsement(supabase, device, body);

      case "revoke":
        return await handleRevocation(supabase, device, body);

      default:
        return Response.json({ error: "Invalid action" }, { status: 400 });
    }
  } catch (error) {
    console.error("Baptism error:", error);
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}

async function handleBaptismRequest(
  supabase: any,
  device: any,
  body: BaptismRequestBody
): Promise<Response> {
  // Check if already verified
  if (device.is_verified) {
    return Response.json({
      success: true,
      message: "Already baptized",
      status: "baptized",
    });
  }

  // Check for existing pending request
  const { data: existing } = await supabase
    .from("baptism_requests")
    .select("id")
    .eq("device_id", device.id)
    .eq("status", "pending")
    .single();

  if (existing) {
    return Response.json({
      success: true,
      message: "Baptism request already pending",
      status: "pending",
    });
  }

  // Create baptism request
  const { error } = await supabase.from("baptism_requests").insert({
    device_id: device.id,
    message: body.payload.message || "",
    status: "pending",
  });

  if (error) {
    return Response.json({ error: "Failed to create request" }, { status: 500 });
  }

  return Response.json({
    success: true,
    message: "Baptism request submitted",
    status: "pending",
  });
}

async function handleEndorsement(
  supabase: any,
  endorser: any,
  body: BaptismRequestBody
): Promise<Response> {
  // Endorser must be verified
  if (!endorser.is_verified) {
    return Response.json(
      { error: "Only verified devices can endorse others" },
      { status: 403 }
    );
  }

  const targetKey = body.payload.target_public_key;
  if (!targetKey) {
    return Response.json({ error: "Missing target_public_key" }, { status: 400 });
  }

  // Find target device
  const { data: target, error: targetError } = await supabase
    .from("devices")
    .select("*")
    .eq("public_key", targetKey)
    .single();

  if (targetError || !target) {
    return Response.json({ error: "Target device not found" }, { status: 404 });
  }

  // Can't self-endorse
  if (target.id === endorser.id) {
    return Response.json({ error: "Cannot endorse yourself" }, { status: 400 });
  }

  // Check for existing endorsement
  const { data: existingEndorsement } = await supabase
    .from("baptism_endorsements")
    .select("id")
    .eq("endorser_id", endorser.id)
    .eq("endorsed_id", target.id)
    .single();

  if (existingEndorsement) {
    return Response.json({
      success: true,
      message: "Already endorsed this device",
    });
  }

  // Calculate endorser's trust level (based on their own endorsements)
  const { count: endorserEndorsements } = await supabase
    .from("baptism_endorsements")
    .select("*", { count: "exact", head: true })
    .eq("endorsed_id", endorser.id);

  const trustLevel = Math.min(5, 1 + Math.floor((endorserEndorsements || 0) / 2));

  // Create endorsement
  const { error: endorseError } = await supabase.from("baptism_endorsements").insert({
    endorser_id: endorser.id,
    endorsed_id: target.id,
    message: body.payload.message || "",
    trust_level: trustLevel,
    signature: body.signature,
  });

  if (endorseError) {
    return Response.json({ error: "Failed to create endorsement" }, { status: 500 });
  }

  // Check if target now qualifies for baptism
  const { data: allEndorsements } = await supabase
    .from("baptism_endorsements")
    .select("trust_level")
    .eq("endorsed_id", target.id);

  const endorsements = allEndorsements || [];

  if (endorsements.length >= MIN_ENDORSEMENTS) {
    // Calculate trust score
    const trustScore = endorsements
      .sort((a: any, b: any) => b.trust_level - a.trust_level)
      .reduce((score: number, e: any, i: number) => {
        const multiplier = 1.0 / (1 + i * 0.3);
        return score + e.trust_level * multiplier;
      }, 0);

    if (trustScore >= TRUST_THRESHOLD) {
      // Baptize the device!
      await supabase
        .from("devices")
        .update({ is_verified: true })
        .eq("id", target.id);

      // Update any pending request
      await supabase
        .from("baptism_requests")
        .update({ status: "approved" })
        .eq("device_id", target.id)
        .eq("status", "pending");

      return Response.json({
        success: true,
        message: "Endorsement recorded. Device is now baptized!",
        baptized: true,
        trust_score: trustScore,
      });
    }
  }

  return Response.json({
    success: true,
    message: "Endorsement recorded",
    endorsement_count: endorsements.length,
    needed: MIN_ENDORSEMENTS,
  });
}

async function handleRevocation(
  supabase: any,
  revoker: any,
  body: BaptismRequestBody
): Promise<Response> {
  // Only verified devices with high trust can revoke
  if (!revoker.is_verified) {
    return Response.json(
      { error: "Only verified devices can revoke endorsements" },
      { status: 403 }
    );
  }

  const targetKey = body.payload.target_public_key;
  if (!targetKey) {
    return Response.json({ error: "Missing target_public_key" }, { status: 400 });
  }

  // Remove the revoker's endorsement of target
  const { data: target } = await supabase
    .from("devices")
    .select("id")
    .eq("public_key", targetKey)
    .single();

  if (!target) {
    return Response.json({ error: "Target not found" }, { status: 404 });
  }

  const { error } = await supabase
    .from("baptism_endorsements")
    .delete()
    .eq("endorser_id", revoker.id)
    .eq("endorsed_id", target.id);

  if (error) {
    return Response.json({ error: "Failed to revoke" }, { status: 500 });
  }

  // Check if target still qualifies
  const { data: remaining } = await supabase
    .from("baptism_endorsements")
    .select("trust_level")
    .eq("endorsed_id", target.id);

  const endorsements = remaining || [];
  const trustScore = endorsements.reduce((s: number, e: any, i: number) => {
    return s + e.trust_level / (1 + i * 0.3);
  }, 0);

  if (endorsements.length < MIN_ENDORSEMENTS || trustScore < TRUST_THRESHOLD) {
    // Revoke baptism
    await supabase
      .from("devices")
      .update({ is_verified: false })
      .eq("id", target.id);

    return Response.json({
      success: true,
      message: "Endorsement revoked. Device baptism status revoked.",
      revoked_baptism: true,
    });
  }

  return Response.json({
    success: true,
    message: "Endorsement revoked",
  });
}

// GET - Status and pending requests
export async function GET(request: Request): Promise<Response> {
  try {
    const url = new URL(request.url);
    const publicKey = url.searchParams.get("public_key");
    const getPending = url.searchParams.get("pending") === "true";

    const supabase = getSupabase();

    if (getPending) {
      // Get pending baptism requests (for verified devices to see)
      const { data: requests, error } = await supabase
        .from("baptism_requests")
        .select(`
          id,
          message,
          created_at,
          device_id,
          devices!inner(name, public_key)
        `)
        .eq("status", "pending")
        .order("created_at", { ascending: false })
        .limit(20);

      if (error) {
        return Response.json({ error: "Failed to fetch" }, { status: 500 });
      }

      const formatted = (requests || []).map((r: any) => ({
        id: r.id,
        device_name: r.devices?.name || "Unknown",
        device_public_key: r.devices?.public_key,
        message: r.message,
        created_at: r.created_at,
      }));

      return Response.json({ success: true, requests: formatted });
    }

    if (!publicKey) {
      return Response.json({ error: "Missing public_key" }, { status: 400 });
    }

    // Get baptism status for specific device
    const { data: device, error: deviceError } = await supabase
      .from("devices")
      .select("id, name, is_verified")
      .eq("public_key", publicKey)
      .single();

    if (deviceError || !device) {
      return Response.json({ error: "Device not found" }, { status: 404 });
    }

    // Get endorsements
    const { data: endorsements } = await supabase
      .from("baptism_endorsements")
      .select(`
        trust_level,
        message,
        created_at,
        endorser_id,
        devices!baptism_endorsements_endorser_id_fkey(name)
      `)
      .eq("endorsed_id", device.id);

    const formattedEndorsements = (endorsements || []).map((e: any) => ({
      endorser_name: e.devices?.name || "Unknown",
      trust_level: e.trust_level,
      message: e.message,
      created_at: e.created_at,
    }));

    // Calculate trust score
    const trustScore = formattedEndorsements
      .sort((a: any, b: any) => b.trust_level - a.trust_level)
      .reduce((score: number, e: any, i: number) => {
        return score + e.trust_level / (1 + i * 0.3);
      }, 0);

    return Response.json({
      success: true,
      device_name: device.name,
      is_verified: device.is_verified,
      status: device.is_verified ? "baptized" : "unbaptized",
      endorsement_count: formattedEndorsements.length,
      trust_score: trustScore,
      threshold: TRUST_THRESHOLD,
      endorsements: formattedEndorsements,
    });
  } catch (error) {
    console.error("Baptism status error:", error);
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}
