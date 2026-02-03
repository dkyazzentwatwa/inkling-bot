/**
 * Project Inkling - Lineage API
 *
 * Birth certificate registration and lineage queries.
 *
 * POST /api/lineage - Register a birth certificate (parent creates for child)
 * GET /api/lineage?public_key=X - Get lineage info for a device
 * GET /api/lineage?public_key=X&children=true - Get device's children
 */

import { verifySignedPayload } from "../../../lib/crypto";
import {
  getOrCreateDevice,
  isDeviceBanned,
  getSupabase,
} from "../../../lib/supabase";

interface BirthCertificateRequest {
  payload: {
    child_public_key: string;
    child_name: string;
    child_hardware_hash: string;
    inherited_traits: Record<string, number>;
  };
  timestamp: number;
  hardware_hash: string;
  public_key: string;  // Parent's public key
  signature: string;
  nonce?: string;
}

// POST - Register birth certificate
export async function POST(request: Request): Promise<Response> {
  try {
    const body = await request.json() as BirthCertificateRequest;

    // Validate required fields
    if (
      !body.payload?.child_public_key ||
      !body.payload?.child_name ||
      !body.payload?.child_hardware_hash ||
      !body.payload?.inherited_traits ||
      !body.public_key ||
      !body.signature
    ) {
      return Response.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    // Verify parent's signature
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

    // Check if parent is banned
    if (await isDeviceBanned(body.public_key)) {
      return Response.json({ error: "Device is banned" }, { status: 403 });
    }

    const supabase = getSupabase();

    // Get parent device
    const parent = await getOrCreateDevice(body.public_key, body.hardware_hash);

    // Check if child already exists
    const { data: existingChild } = await supabase
      .from("devices")
      .select("id, parent_id")
      .eq("public_key", body.payload.child_public_key)
      .single();

    if (existingChild) {
      if (existingChild.parent_id) {
        return Response.json(
          { error: "Child device already has a parent" },
          { status: 409 }
        );
      }

      // Update existing device with lineage info
      const { error: updateError } = await supabase
        .from("devices")
        .update({
          name: body.payload.child_name,
          parent_id: parent.id,
          generation: (parent.generation || 0) + 1,
          metadata: {
            inherited_traits: body.payload.inherited_traits,
            birth_certificate: {
              parent_public_key: body.public_key,
              parent_name: parent.name,
              birth_timestamp: new Date().toISOString(),
              signature: body.signature,
            },
          },
        })
        .eq("id", existingChild.id);

      if (updateError) {
        console.error("Failed to update child device:", updateError);
        return Response.json(
          { error: "Failed to register birth certificate" },
          { status: 500 }
        );
      }

      return Response.json({
        success: true,
        message: "Birth certificate registered for existing device",
        child_id: existingChild.id,
        generation: (parent.generation || 0) + 1,
      });
    }

    // Create new child device
    const { data: child, error: insertError } = await supabase
      .from("devices")
      .insert({
        public_key: body.payload.child_public_key,
        hardware_hash: body.payload.child_hardware_hash,
        name: body.payload.child_name,
        parent_id: parent.id,
        generation: (parent.generation || 0) + 1,
        is_verified: false,
        metadata: {
          inherited_traits: body.payload.inherited_traits,
          birth_certificate: {
            parent_public_key: body.public_key,
            parent_name: parent.name,
            birth_timestamp: new Date().toISOString(),
            signature: body.signature,
          },
        },
      })
      .select()
      .single();

    if (insertError) {
      console.error("Failed to create child device:", insertError);
      return Response.json(
        { error: "Failed to register birth certificate" },
        { status: 500 }
      );
    }

    return Response.json({
      success: true,
      message: "Birth certificate registered",
      child_id: child.id,
      child_name: child.name,
      generation: child.generation,
      parent_name: parent.name,
    });
  } catch (error) {
    console.error("Lineage registration error:", error);
    return Response.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

// GET - Query lineage info
export async function GET(request: Request): Promise<Response> {
  try {
    const url = new URL(request.url);
    const publicKey = url.searchParams.get("public_key");
    const getChildren = url.searchParams.get("children") === "true";

    if (!publicKey) {
      return Response.json(
        { error: "Missing public_key parameter" },
        { status: 400 }
      );
    }

    const supabase = getSupabase();

    // Get device
    const { data: device, error: deviceError } = await supabase
      .from("devices")
      .select("id, name, public_key, parent_id, generation, metadata, created_at")
      .eq("public_key", publicKey)
      .single();

    if (deviceError || !device) {
      return Response.json(
        { error: "Device not found" },
        { status: 404 }
      );
    }

    // Get parent info if exists
    let parentInfo = null;
    if (device.parent_id) {
      const { data: parent } = await supabase
        .from("devices")
        .select("name, public_key")
        .eq("id", device.parent_id)
        .single();

      if (parent) {
        parentInfo = {
          name: parent.name,
          public_key: parent.public_key,
        };
      }
    }

    // Get children count
    const { count: childrenCount } = await supabase
      .from("devices")
      .select("*", { count: "exact", head: true })
      .eq("parent_id", device.id);

    const lineageInfo = {
      device_id: device.id,
      name: device.name,
      generation: device.generation || 0,
      parent: parentInfo,
      children_count: childrenCount || 0,
      inherited_traits: device.metadata?.inherited_traits || null,
      birth_certificate: device.metadata?.birth_certificate || null,
      created_at: device.created_at,
    };

    // Optionally include children list
    if (getChildren) {
      const { data: children } = await supabase
        .from("devices")
        .select("id, name, public_key, generation, created_at")
        .eq("parent_id", device.id)
        .order("created_at", { ascending: false })
        .limit(50);

      return Response.json({
        success: true,
        lineage: lineageInfo,
        children: children || [],
      });
    }

    return Response.json({
      success: true,
      lineage: lineageInfo,
    });
  } catch (error) {
    console.error("Lineage query error:", error);
    return Response.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
