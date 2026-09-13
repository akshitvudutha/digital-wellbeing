/**
 * Supabase server-side client for internal API routes.
 *
 * Uses the SERVICE_ROLE key so that RLS-protected tables can be written to
 * without a user session.  This module must NEVER be imported from client
 * components — it is server-only (Node.js / Edge runtime on Vercel).
 *
 * Environment variables required (set in Vercel dashboard, never in .env.local):
 *   SUPABASE_URL              – Project URL  (e.g. https://xxxx.supabase.co)
 *   SUPABASE_SERVICE_ROLE_KEY – Service-role secret key
 */

import { createClient } from '@supabase/supabase-js';

let _client: ReturnType<typeof createClient> | null = null;

export function getSupabaseServiceClient() {
  if (_client) return _client;

  const url = process.env.SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !serviceRoleKey) {
    throw new Error(
      '[Supabase] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set as Vercel environment variables.'
    );
  }

  _client = createClient(url, serviceRoleKey, {
    auth: {
      // Disable auto-refresh and session persistence — this is a server-only client.
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  return _client;
}
