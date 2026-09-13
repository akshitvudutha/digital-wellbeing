import { validateEmail } from './service';
import { sendBetaApprovalEmail } from '@/lib/email/resend';
import { getSupabaseServiceClient } from '@/lib/supabase/client';
import type { Resend } from 'resend';
import type { SupabaseClient } from '@supabase/supabase-js';

export const DEFAULT_NOTCH_DOWNLOAD_URL =
  'https://github.com/akshitvudutha/digital-wellbeing/releases/download/v3.1.6/NotchSetup-3.1.6.exe';

export interface ApproveBetaUserOptions {
  email?: string;
  id?: string;
  downloadUrl?: string;
  fromEmail?: string;
  resendClient?: Resend;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  supabaseClient?: SupabaseClient<any, any, any>;
}

export type ApprovalResultCode =
  | 'APPROVED_AND_SENT'
  | 'ALREADY_SENT'
  | 'NOT_FOUND'
  | 'INVALID_REQUEST'
  | 'CONFIG_ERROR'
  | 'EMAIL_FAILED'
  | 'DB_ERROR';

export interface ApproveBetaUserResult {
  success: boolean;
  code: ApprovalResultCode;
  message: string;
  email?: string;
  approvalEmailSentAt?: string;
  error?: string;
}

/**
 * Executes the secure beta approval workflow for a single tester:
 * 1. Verifies configuration and resolves the Supabase client.
 * 2. Fetches the beta_requests record from Supabase.
 * 3. Prevents duplicate sends if approval_email_sent_at is already set.
 * 4. Dispatches the branded approval email containing the installer download link via Resend.
 * 5. Only upon verified send success, updates status to 'approved' and stamps approved_at & approval_email_sent_at.
 * 6. If email fails, database is NOT marked as sent so it can be retried safely.
 */
export async function approveBetaUser(
  options: ApproveBetaUserOptions
): Promise<ApproveBetaUserResult> {
  const targetEmail = (options.email || '').trim().toLowerCase();
  const targetId = (options.id || '').trim();

  if (!targetEmail && !targetId) {
    return {
      success: false,
      code: 'INVALID_REQUEST',
      message: 'Either email or id must be provided.',
    };
  }

  if (targetEmail && !validateEmail(targetEmail)) {
    return {
      success: false,
      code: 'INVALID_REQUEST',
      message: 'A valid email address is required.',
    };
  }

  // Resolve download URL (from options, env, or default)
  const downloadUrl = (options.downloadUrl || process.env.NOTCH_DOWNLOAD_URL || DEFAULT_NOTCH_DOWNLOAD_URL).trim();

  // Configuration check: Sender Email
  const fromEmail = options.fromEmail || process.env.RESEND_FROM_EMAIL;
  if (!fromEmail || fromEmail.trim() === '') {
    return {
      success: false,
      code: 'CONFIG_ERROR',
      message: 'RESEND_FROM_EMAIL environment variable is not configured.',
    };
  }

  // Configuration check: Resend API Key
  if (!options.resendClient && (!process.env.RESEND_API_KEY || process.env.RESEND_API_KEY.trim() === '')) {
    return {
      success: false,
      code: 'CONFIG_ERROR',
      message: 'RESEND_API_KEY environment variable is not configured.',
    };
  }

  // Initialize or resolve Supabase service client
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let supabase: SupabaseClient<any, any, any>;
  try {
    supabase = options.supabaseClient || getSupabaseServiceClient();
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Failed to initialize database client';
    return {
      success: false,
      code: 'CONFIG_ERROR',
      message: errorMsg,
    };
  }

  // 1. Fetch user record from beta_requests
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let query = (supabase.from('beta_requests') as any).select('*');
    if (targetEmail) {
      query = query.eq('email', targetEmail);
    } else {
      query = query.eq('id', targetId);
    }

    const { data: record, error: fetchError } = await query.maybeSingle();

    if (fetchError) {
      console.error('[Beta Approval] Error querying beta_requests:', fetchError.message);
      return {
        success: false,
        code: 'DB_ERROR',
        message: 'Database query failed.',
        error: fetchError.message,
      };
    }

    if (!record) {
      return {
        success: false,
        code: 'NOT_FOUND',
        message: `Beta request for "${targetEmail || targetId}" not found.`,
      };
    }

    const recipientEmail = record.email;

    // 2. Guard against duplicate approval email sends
    if (record.approval_email_sent_at) {
      return {
        success: false,
        code: 'ALREADY_SENT',
        message: `Approval email has already been sent to ${recipientEmail}.`,
        email: recipientEmail,
        approvalEmailSentAt: record.approval_email_sent_at,
      };
    }

    // 3. Send email via Resend with the installer download link
    const sendResult = await sendBetaApprovalEmail({
      to: recipientEmail,
      downloadUrl,
      fromEmail: fromEmail.trim(),
      resendClient: options.resendClient,
    });

    if (!sendResult.success) {
      // Do NOT update approval_email_sent_at in DB, so request can be retried
      return {
        success: false,
        code: 'EMAIL_FAILED',
        message: 'Failed to send approval email via Resend.',
        email: recipientEmail,
        error: sendResult.error,
      };
    }

    // 4. Record successful email send in database
    const now = new Date().toISOString();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { error: updateError } = await (supabase.from('beta_requests') as any)
      .update({
        status: 'approved',
        approved_at: record.approved_at || now,
        approval_email_sent_at: now,
      })
      .eq('email', recipientEmail);

    if (updateError) {
      console.error('[Beta Approval] Email sent but failed to update status:', updateError.message);
      return {
        success: false,
        code: 'DB_ERROR',
        message: 'Approval email sent, but failed to record timestamp in database.',
        email: recipientEmail,
        error: updateError.message,
      };
    }

    return {
      success: true,
      code: 'APPROVED_AND_SENT',
      message: 'Beta access approved and email sent successfully.',
      email: recipientEmail,
      approvalEmailSentAt: now,
    };
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Unexpected server error';
    console.error('[Beta Approval Exception]:', errorMsg);
    return {
      success: false,
      code: 'DB_ERROR',
      message: 'An unexpected error occurred while processing approval.',
      error: errorMsg,
    };
  }
}
