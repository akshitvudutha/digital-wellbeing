import crypto from 'crypto';

/**
 * Constant-time comparison between two strings.
 *
 * To prevent timing attacks that might leak the length of the secret,
 * both inputs are hashed with SHA-256 before applying crypto.timingSafeEqual.
 */
export function constantTimeCompare(a: string, b: string): boolean {
  if (typeof a !== 'string' || typeof b !== 'string') {
    return false;
  }

  try {
    const aHash = crypto.createHash('sha256').update(a).digest();
    const bHash = crypto.createHash('sha256').update(b).digest();
    return crypto.timingSafeEqual(aHash, bHash);
  } catch {
    return false;
  }
}

export interface AdminAuthValidationResult {
  authorized: boolean;
  error?: 'CONFIG_MISSING' | 'INVALID_SECRET' | 'HEADER_MISSING';
}

/**
 * Validates an incoming secret token against the server-side BETA_ADMIN_SECRET environment variable.
 * Supports raw secret strings or Bearer tokens.
 *
 * Note: Never logs, echoes, or returns the admin secret.
 */
export function validateAdminAuth(rawAuthHeaderOrSecret: string | null | undefined): AdminAuthValidationResult {
  const configuredSecret = process.env.BETA_ADMIN_SECRET;

  if (!configuredSecret || configuredSecret.trim() === '') {
    return {
      authorized: false,
      error: 'CONFIG_MISSING',
    };
  }

  if (!rawAuthHeaderOrSecret || rawAuthHeaderOrSecret.trim() === '') {
    return {
      authorized: false,
      error: 'HEADER_MISSING',
    };
  }

  let token = rawAuthHeaderOrSecret.trim();
  if (token.toLowerCase().startsWith('bearer ')) {
    token = token.slice(7).trim();
  }

  const isValid = constantTimeCompare(token, configuredSecret.trim());
  if (!isValid) {
    return {
      authorized: false,
      error: 'INVALID_SECRET',
    };
  }

  return {
    authorized: true,
  };
}
