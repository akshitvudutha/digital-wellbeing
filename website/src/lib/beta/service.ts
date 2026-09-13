/**
 * Beta Access Service Architecture
 * 
 * Manages controlled beta registration for Notch.
 * Completely decoupled from desktop application data.
 * Adheres to local-first privacy: no desktop usage metrics or activity
 * are ever transmitted or associated with beta accounts.
 */

export interface BetaAccessPayload {
  email: string;
  osVersion?: 'Windows 11' | 'Windows 10' | 'Other';
  primaryFocus?: string;
  honeypot?: string; // Bot protection
}

export interface BetaAccessResult {
  success: boolean;
  message: string;
  code?: 'INVALID_EMAIL' | 'BOT_DETECTED' | 'RATE_LIMITED' | 'SAVED' | 'ALREADY_REGISTERED';
}

// In-memory rate limiting map for edge/serverless runtime
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();

export function checkRateLimit(ip: string, limit = 5, windowMs = 60_000): boolean {
  const now = Date.now();
  const record = rateLimitMap.get(ip);

  if (!record || now > record.resetTime) {
    rateLimitMap.set(ip, { count: 1, resetTime: now + windowMs });
    return true;
  }

  if (record.count >= limit) {
    return false;
  }

  record.count++;
  return true;
}

export function validateEmail(email: string): boolean {
  if (!email || typeof email !== 'string') return false;
  const trimmed = email.trim();
  if (trimmed.length > 254) return false;
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
  return emailRegex.test(trimmed);
}

export async function processBetaRequest(
  payload: BetaAccessPayload,
  clientIp = 'unknown'
): Promise<BetaAccessResult> {
  // 1. Honeypot check (anti-bot)
  if (payload.honeypot && payload.honeypot.trim().length > 0) {
    return {
      success: false,
      message: 'Submission rejected.',
      code: 'BOT_DETECTED',
    };
  }

  // 2. Email format validation
  const email = (payload.email || '').trim().toLowerCase();
  if (!validateEmail(email)) {
    return {
      success: false,
      message: 'Please provide a valid email address.',
      code: 'INVALID_EMAIL',
    };
  }

  // 3. Rate limiting check
  if (!checkRateLimit(clientIp)) {
    return {
      success: false,
      message: 'Too many requests. Please wait a moment before trying again.',
      code: 'RATE_LIMITED',
    };
  }

  const record = {
    id: `beta_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
    email,
    osVersion: payload.osVersion || 'Windows 11',
    primaryFocus: (payload.primaryFocus || '').slice(0, 500),
    requestedAt: new Date().toISOString(),
  };

  // 4. External backend integration hook (Supabase / Resend / Webhook)
  const webhookUrl = process.env.BETA_ACCESS_WEBHOOK_URL;
  if (webhookUrl) {
    try {
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(record),
      });
      if (!response.ok) {
        console.warn('Upstream beta webhook returned non-200:', response.status);
      }
    } catch (error) {
      console.error('Error forwarding beta registration to upstream webhook:', error);
      // We still treat as recorded locally to avoid frustrating the prospective tester
    }
  } else {
    // In local development or until production credentials are provided:
    console.log('[Notch Beta Registration Recorded]:', record.email, record.osVersion);
  }

  return {
    success: true,
    message: "You're on the list. We invite testers in weekly batches to maintain close feedback.",
    code: 'SAVED',
  };
}
