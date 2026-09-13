import { Resend } from 'resend';

export interface SendBetaApprovalEmailOptions {
  to: string;
  downloadUrl?: string;
  fromEmail?: string;
  resendClient?: Resend;
}

export interface SendEmailResult {
  success: boolean;
  id?: string;
  error?: string;
}

/**
 * Returns a configured Resend instance or null if RESEND_API_KEY is not set.
 */
export function getResendClient(customApiKey?: string): Resend | null {
  const apiKey = customApiKey || process.env.RESEND_API_KEY;
  if (!apiKey || apiKey.trim() === '') {
    return null;
  }
  return new Resend(apiKey.trim());
}

/**
 * Generates the clean plain-text version of the beta approval email.
 */
export function generateBetaApprovalEmailText(downloadUrl: string): string {
  return `Notch

Your beta access has been approved.

You can now download Notch for Windows:
${downloadUrl}

Version: 3.1.6

Notch is a local-first digital wellbeing and attention-control app for Windows.

Privacy:
Notch's desktop core is designed to work locally without requiring an account or cloud sync.
`;
}

/**
 * Generates the responsive HTML version of the beta approval email.
 * Inline CSS ensures consistent rendering across major email clients.
 */
export function generateBetaApprovalEmailHtml(downloadUrl: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Notch beta access is ready</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0c0e12; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0; -webkit-font-smoothing: antialiased;">
  <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed;">
    <tr>
      <td align="center" style="padding: 48px 16px;">
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 560px; background-color: #141720; border: 1px solid #232a3b; border-radius: 12px; overflow: hidden;">
          <!-- Header -->
          <tr>
            <td style="padding: 36px 36px 20px 36px;">
              <span style="display: inline-block; font-size: 20px; font-weight: 700; letter-spacing: -0.02em; color: #ffffff; text-decoration: none;">Notch</span>
            </td>
          </tr>
          <!-- Body Content -->
          <tr>
            <td style="padding: 0 36px 28px 36px;">
              <h1 style="margin: 0 0 12px 0; font-size: 24px; font-weight: 600; line-height: 1.3; color: #ffffff; letter-spacing: -0.01em;">
                Your beta access has been approved.
              </h1>
              <p style="margin: 0 0 28px 0; font-size: 15px; line-height: 1.6; color: #94a3b8;">
                You can now download Notch for Windows.
              </p>
              
              <!-- Download CTA Button -->
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="margin-bottom: 28px;">
                <tr>
                  <td align="center" style="border-radius: 8px; background-color: #2563eb;">
                    <a href="${downloadUrl}" target="_blank" rel="noopener noreferrer" style="display: inline-block; padding: 12px 28px; font-size: 15px; font-weight: 600; color: #ffffff; text-decoration: none; border-radius: 8px;">
                      Download Notch
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin: 0 0 24px 0; font-size: 13px; color: #64748b;">
                Version 3.1.6
              </p>

              <!-- App Description & Privacy Note -->
              <div style="padding-top: 20px; border-top: 1px solid #232a3b;">
                <p style="margin: 0 0 12px 0; font-size: 14px; line-height: 1.5; color: #cbd5e1;">
                  Notch is a local-first digital wellbeing and attention-control app for Windows.
                </p>
                <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #94a3b8;">
                  <strong style="color: #cbd5e1;">Privacy:</strong> Notch&apos;s desktop core is designed to work locally without requiring an account or cloud sync.
                </p>
              </div>
            </td>
          </tr>
          <!-- Footer fallback URL -->
          <tr>
            <td style="padding: 20px 36px; background-color: #0f1219; border-top: 1px solid #1c2230; font-size: 12px; line-height: 1.5; color: #64748b; word-break: break-all;">
              Direct download link:<br>
              <a href="${downloadUrl}" style="color: #3b82f6; text-decoration: none;">${downloadUrl}</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
}

/**
 * Dispatches the beta approval email using Resend.
 * Validates configuration and handles errors gracefully without exposing sensitive credentials.
 */
export async function sendBetaApprovalEmail(
  options: SendBetaApprovalEmailOptions
): Promise<SendEmailResult> {
  const { to } = options;

  if (!to || typeof to !== 'string' || to.trim() === '') {
    return {
      success: false,
      error: 'Recipient email address is required.',
    };
  }

  // 1. Resolve & validate download URL
  const downloadUrl = options.downloadUrl || process.env.NOTCH_DOWNLOAD_URL;
  if (!downloadUrl || downloadUrl.trim() === '') {
    return {
      success: false,
      error: 'Installer download URL is not provided.',
    };
  }

  // 2. Resolve & validate sender address
  const fromEmail = options.fromEmail || process.env.RESEND_FROM_EMAIL;
  if (!fromEmail || fromEmail.trim() === '') {
    return {
      success: false,
      error: 'RESEND_FROM_EMAIL environment variable is not configured.',
    };
  }

  // 3. Initialize Resend client
  const resend = options.resendClient || getResendClient();
  if (!resend) {
    return {
      success: false,
      error: 'RESEND_API_KEY environment variable is not configured.',
    };
  }

  const subject = 'Your Notch beta access is ready';
  const text = generateBetaApprovalEmailText(downloadUrl.trim());
  const html = generateBetaApprovalEmailHtml(downloadUrl.trim());

  try {
    const { data, error } = await resend.emails.send({
      from: fromEmail.trim(),
      to: to.trim().toLowerCase(),
      subject,
      text,
      html,
    });

    if (error) {
      console.error('[Resend Error]:', error.name, error.message);
      return {
        success: false,
        error: error.message || 'Failed to send email via Resend.',
      };
    }

    return {
      success: true,
      id: data?.id,
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Unknown email dispatch error';
    console.error('[Resend Exception]:', message);
    return {
      success: false,
      error: message,
    };
  }
}
