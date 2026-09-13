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

/**
 * Simple one-way hash of an IP address for privacy-preserving storage.
 * We never need to reverse it; it is only used for deduplication/analytics.
 */
async function hashIp(ip: string): Promise<string> {
  try {
    const encoder = new TextEncoder();
    const data = encoder.encode(ip);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 16);
  } catch {
    return 'unknown';
  }
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

  // 4. Persist to Supabase (server-side only, service-role key)
  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (supabaseUrl && supabaseKey) {
    try {
      const { getSupabaseServiceClient } = await import('@/lib/supabase/client');
      const supabase = getSupabaseServiceClient();

      const ipHash = await hashIp(clientIp);

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { error } = await (supabase.from('beta_requests') as any).insert({
        email,
        os_version: payload.osVersion || null,
        primary_focus: (payload.primaryFocus || '').slice(0, 500) || null,
        ip_hash: ipHash,
      });



      if (error) {
        // Postgres unique-violation code = 23505
        if (error.code === '23505') {
          return {
            success: true,
            message: "You're already on the list — we'll be in touch soon.",
            code: 'ALREADY_REGISTERED',
          };
        }
        // Log other DB errors but do not surface internal details to the client
        console.error('[Notch Beta] Supabase insert error:', error.message);
      }
    } catch (err) {
      console.error('[Notch Beta] Unexpected Supabase error:', err);
      // Fail open: we still acknowledge the request to avoid frustrating the user
    }
  } else {
    // Local development / env vars not yet configured
    console.log('[Notch Beta Registration - local only]:', email, payload.osVersion);
  }

  return {
    success: true,
    message: "You're on the list. We invite testers in weekly batches to maintain close feedback.",
    code: 'SAVED',
  };
}
