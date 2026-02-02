/**
 * Project Inkling - Cryptographic Verification
 *
 * Server-side Ed25519 signature verification for device authentication.
 */

import { createHash, randomBytes } from "crypto";

// Ed25519 verification using Web Crypto API (Edge-compatible)
export async function verifyEd25519Signature(
  publicKeyHex: string,
  signatureHex: string,
  message: Uint8Array
): Promise<boolean> {
  try {
    // Convert hex to bytes
    const publicKeyBytes = hexToBytes(publicKeyHex);
    const signatureBytes = hexToBytes(signatureHex);

    // Import public key
    const publicKey = await crypto.subtle.importKey(
      "raw",
      publicKeyBytes,
      { name: "Ed25519" },
      false,
      ["verify"]
    );

    // Verify signature
    return await crypto.subtle.verify("Ed25519", publicKey, signatureBytes, message);
  } catch (error) {
    console.error("Signature verification failed:", error);
    return false;
  }
}

/**
 * Verify a signed payload from an Inkling device.
 */
export async function verifySignedPayload(
  data: {
    payload: Record<string, unknown>;
    timestamp: number;
    hardware_hash: string;
    public_key: string;
    signature: string;
    nonce?: string | null;
  },
  maxAgeSeconds: number = 300
): Promise<{ valid: boolean; error?: string }> {
  // Check timestamp freshness
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - data.timestamp) > maxAgeSeconds) {
    return { valid: false, error: "Signature expired" };
  }

  // Reconstruct signing material (must match Python implementation)
  const signData: Record<string, unknown> = {
    payload: data.payload,
    timestamp: data.timestamp,
    hardware_hash: data.hardware_hash,
  };
  if (data.nonce) {
    signData.nonce = data.nonce;
  }

  // Sort keys and stringify (matching Python's sort_keys=True)
  const signBytes = new TextEncoder().encode(
    JSON.stringify(signData, Object.keys(signData).sort())
  );

  // Verify signature
  const valid = await verifyEd25519Signature(
    data.public_key,
    data.signature,
    signBytes
  );

  return valid ? { valid: true } : { valid: false, error: "Invalid signature" };
}

/**
 * Generate a random nonce for challenge-response authentication.
 */
export function generateNonce(): string {
  return randomBytes(32).toString("hex");
}

/**
 * Verify challenge-response from device.
 */
export async function verifyChallengeResponse(
  publicKeyHex: string,
  hardwareHash: string,
  nonce: string,
  responseSignatureHex: string
): Promise<boolean> {
  const challengeData = new TextEncoder().encode(`${nonce}:${hardwareHash}`);
  return verifyEd25519Signature(publicKeyHex, responseSignatureHex, challengeData);
}

// Utility: Convert hex string to Uint8Array
function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}

// Utility: Convert Uint8Array to hex string
export function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
