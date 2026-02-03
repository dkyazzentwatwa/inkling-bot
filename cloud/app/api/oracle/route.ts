/**
 * Project Inkling - Oracle API
 *
 * AI proxy endpoint that:
 * 1. Verifies device signature
 * 2. Enforces rate limits
 * 3. Proxies request to Anthropic/OpenAI
 * 4. Returns AI response
 *
 * POST /api/oracle
 * Body: {
 *   payload: { messages: [...], system_prompt: string },
 *   timestamp: number,
 *   hardware_hash: string,
 *   public_key: string,
 *   signature: string,
 *   nonce?: string
 * }
 */

import Anthropic from "@anthropic-ai/sdk";
import OpenAI from "openai";
import { verifySignedPayload } from "../../../lib/crypto";
import {
  getOrCreateDevice,
  isDeviceBanned,
  getRateLimit,
  incrementRateLimit,
  consumeNonce,
} from "../../../lib/supabase";

// Rate limits
const MAX_ORACLE_CALLS_PER_DAY = 100;
const MAX_TOKENS_PER_DAY = 10000;
const MAX_TOKENS_PER_REQUEST = 500;

// AI clients (lazy initialized)
let anthropicClient: Anthropic | null = null;
let openaiClient: OpenAI | null = null;

function getAnthropicClient(): Anthropic | null {
  if (!anthropicClient && process.env.ANTHROPIC_API_KEY) {
    anthropicClient = new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY,
    });
  }
  return anthropicClient;
}

function getOpenAIClient(): OpenAI | null {
  if (!openaiClient && process.env.OPENAI_API_KEY) {
    openaiClient = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });
  }
  return openaiClient;
}

interface OracleRequest {
  payload: {
    messages: Array<{ role: "user" | "assistant"; content: string }>;
    system_prompt: string;
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
    const body = await request.json() as OracleRequest;

    // Validate required fields
    if (
      !body.payload ||
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

    if (rateLimit.oracle_calls >= MAX_ORACLE_CALLS_PER_DAY) {
      return Response.json(
        { error: "Daily call limit exceeded", limit: MAX_ORACLE_CALLS_PER_DAY },
        { status: 429 }
      );
    }

    if (rateLimit.tokens_used >= MAX_TOKENS_PER_DAY) {
      return Response.json(
        { error: "Daily token limit exceeded", limit: MAX_TOKENS_PER_DAY },
        { status: 429 }
      );
    }

    // Increment call counter
    await incrementRateLimit(device.id, "oracle_calls");

    // Try Anthropic first, then OpenAI
    const anthropic = getAnthropicClient();
    const openai = getOpenAIClient();

    let response: { content: string; tokens: number; provider: string; model: string };

    if (anthropic) {
      try {
        response = await callAnthropic(
          anthropic,
          body.payload.system_prompt,
          body.payload.messages
        );
      } catch (error) {
        console.error("Anthropic error:", error);
        if (openai) {
          response = await callOpenAI(
            openai,
            body.payload.system_prompt,
            body.payload.messages
          );
        } else {
          throw error;
        }
      }
    } else if (openai) {
      response = await callOpenAI(
        openai,
        body.payload.system_prompt,
        body.payload.messages
      );
    } else {
      return Response.json(
        { error: "No AI providers configured" },
        { status: 500 }
      );
    }

    // Record token usage
    await incrementRateLimit(device.id, "tokens_used", response.tokens);

    return Response.json({
      content: response.content,
      tokens_used: response.tokens,
      provider: response.provider,
      model: response.model,
      remaining_calls: MAX_ORACLE_CALLS_PER_DAY - rateLimit.oracle_calls - 1,
      remaining_tokens: MAX_TOKENS_PER_DAY - rateLimit.tokens_used - response.tokens,
    });
  } catch (error) {
    console.error("Oracle error:", error);
    return Response.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

async function callAnthropic(
  client: Anthropic,
  systemPrompt: string,
  messages: Array<{ role: "user" | "assistant"; content: string }>
): Promise<{ content: string; tokens: number; provider: string; model: string }> {
  const response = await client.messages.create({
    model: "claude-3-haiku-20240307",
    max_tokens: MAX_TOKENS_PER_REQUEST,
    system: systemPrompt,
    messages: messages.map((m) => ({
      role: m.role,
      content: m.content,
    })),
  });

  const content =
    response.content[0].type === "text" ? response.content[0].text : "";
  const tokens = response.usage.input_tokens + response.usage.output_tokens;

  return {
    content,
    tokens,
    provider: "anthropic",
    model: "claude-3-haiku-20240307",
  };
}

async function callOpenAI(
  client: OpenAI,
  systemPrompt: string,
  messages: Array<{ role: "user" | "assistant"; content: string }>
): Promise<{ content: string; tokens: number; provider: string; model: string }> {
  const response = await client.chat.completions.create({
    model: "gpt-4o-mini",
    max_tokens: MAX_TOKENS_PER_REQUEST,
    messages: [
      { role: "system", content: systemPrompt },
      ...messages.map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      })),
    ],
  });

  const content = response.choices[0]?.message?.content || "";
  const tokens = response.usage?.total_tokens || 0;

  return {
    content,
    tokens,
    provider: "openai",
    model: "gpt-4o-mini",
  };
}

// GET endpoint for challenge nonce
export async function GET(): Promise<Response> {
  const { createChallengeNonce } = await import("../../../lib/supabase");
  const nonce = await createChallengeNonce();

  return Response.json({ nonce });
}
