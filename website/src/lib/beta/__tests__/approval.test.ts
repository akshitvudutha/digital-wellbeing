import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { approveBetaUser, DEFAULT_NOTCH_DOWNLOAD_URL } from '@/lib/beta/approval';
import { validateAdminAuth, constantTimeCompare } from '@/lib/auth/admin';
import { POST } from '@/app/api/beta/approve/route';
import { GET as downloadRouteGet } from '@/app/api/download/route';
import { NextRequest } from 'next/server';
import fs from 'fs';
import path from 'path';

// Helper to create mock Supabase client
function createMockSupabase(initialRecord: Record<string, unknown> | null) {
  let record = initialRecord ? { ...initialRecord } : null;
  let updatePayload: Record<string, unknown> | null = null;
  let updateCallCount = 0;

  return {
    getRecord: () => record,
    getUpdatePayload: () => updatePayload,
    getUpdateCallCount: () => updateCallCount,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    from: (_table: string): any => ({
      select: () => ({
        eq: (_col: string, _val: unknown) => ({
          maybeSingle: async () => ({ data: record, error: null }),
        }),
      }),
      update: (payload: Record<string, unknown>) => {
        updateCallCount++;
        updatePayload = payload;
        return {
          eq: (_col: string, _val: unknown) => {
            if (record) {
              record = { ...record, ...payload };
            }
            return Promise.resolve({ data: record, error: null });
          },
        };
      },
    }),
  };
}

// Helper to create mock Resend client
function createMockResend(options: { fail?: boolean; errorMessage?: string } = {}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sentCalls: any[] = [];
  return {
    sentCalls,
    emails: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      send: async (args: any) => {
        sentCalls.push(args);
        if (options.fail) {
          return {
            data: null,
            error: {
              name: 'resend_error',
              message: options.errorMessage || 'Simulated Resend API dispatch error',
            },
          };
        }
        return {
          data: { id: 'mock_msg_98765' },
          error: null,
        };
      },
    },
  };
}

describe('Notch Beta Approval & Public Release Delivery System', () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    process.env = { ...originalEnv };
    process.env.RESEND_API_KEY = 're_mock_test_key_12345';
    process.env.RESEND_FROM_EMAIL = 'Notch <beta@notch1.vercel.app>';
    process.env.BETA_ADMIN_SECRET = 'notch-super-secret-admin-key-2026';
    delete process.env.NOTCH_DOWNLOAD_URL;
    delete process.env.NOTCH_INSTALLER_PATH;
  });

  // Test 1: Valid approval sends one email with the installer URL
  it('1. Valid approval sends one email containing the installer download URL', async () => {
    const mockDb = createMockSupabase({
      id: 'req_1',
      email: 'tester@example.com',
      status: 'pending',
      approved_at: null,
      approval_email_sent_at: null,
    });
    const mockResend = createMockResend();

    const result = await approveBetaUser({
      email: 'tester@example.com',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      supabaseClient: mockDb as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      resendClient: mockResend as any,
    });

    assert.equal(result.success, true);
    assert.equal(result.code, 'APPROVED_AND_SENT');

    assert.equal(mockResend.sentCalls.length, 1);
    const email = mockResend.sentCalls[0];
    assert.equal(email.to, 'tester@example.com');
    assert.equal(email.from, 'Notch <beta@notch1.vercel.app>');
    assert.equal(email.subject, 'Your Notch beta access is ready');
    // Verifies the download link points to the release URL
    assert.match(email.text, /https:\/\/github\.com\/akshitvudutha\/digital-wellbeing\/releases\/download\/v3\.1\.6\/NotchSetup-3\.1\.6\.exe/);
    assert.match(email.html, /Download Notch/);
    assert.match(email.html, /https:\/\/github\.com\/akshitvudutha\/digital-wellbeing\/releases\/download\/v3\.1\.6\/NotchSetup-3\.1\.6\.exe/);
    assert.match(email.text, /Version: 3\.1\.6/);
    assert.match(email.text, /local-first digital wellbeing/);
    assert.match(email.text, /Privacy:/);
  });

  // Test 2: Custom NOTCH_DOWNLOAD_URL override works properly
  it('2. Custom NOTCH_DOWNLOAD_URL environment variable overrides default download URL', async () => {
    process.env.NOTCH_DOWNLOAD_URL = 'https://custom-cdn.example.com/NotchSetup-3.1.6.exe';

    const mockDb = createMockSupabase({
      id: 'req_2',
      email: 'tester2@example.com',
      status: 'pending',
      approved_at: null,
      approval_email_sent_at: null,
    });
    const mockResend = createMockResend();

    const result = await approveBetaUser({
      email: 'tester2@example.com',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      supabaseClient: mockDb as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      resendClient: mockResend as any,
    });

    assert.equal(result.success, true);
    const email = mockResend.sentCalls[0];
    assert.match(email.text, /https:\/\/custom-cdn\.example\.com\/NotchSetup-3\.1\.6\.exe/);
  });

  // Test 3: Successful email records approval_email_sent_at in database
  it('3. Successful email records approval_email_sent_at in database', async () => {
    const mockDb = createMockSupabase({
      id: 'req_3',
      email: 'tester3@example.com',
      status: 'pending',
      approved_at: null,
      approval_email_sent_at: null,
    });
    const mockResend = createMockResend();

    const result = await approveBetaUser({
      email: 'tester3@example.com',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      supabaseClient: mockDb as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      resendClient: mockResend as any,
    });

    assert.equal(result.success, true);
    const updated = mockDb.getRecord();
    assert.equal(updated?.status, 'approved');
    assert.ok(updated?.approved_at);
    assert.ok(updated?.approval_email_sent_at);
    assert.equal(mockDb.getUpdateCallCount(), 1);
  });

  // Test 4: Resend failure does not record the email as sent (retryable)
  it('4. Resend failure does not record the email as sent so it can be retried', async () => {
    const mockDb = createMockSupabase({
      id: 'req_4',
      email: 'tester4@example.com',
      status: 'pending',
      approved_at: null,
      approval_email_sent_at: null,
    });
    const mockResend = createMockResend({ fail: true, errorMessage: 'API Key Quota Exceeded' });

    const result = await approveBetaUser({
      email: 'tester4@example.com',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      supabaseClient: mockDb as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      resendClient: mockResend as any,
    });

    assert.equal(result.success, false);
    assert.equal(result.code, 'EMAIL_FAILED');
    assert.match(result.error || '', /API Key Quota Exceeded/);
    assert.equal(mockDb.getUpdateCallCount(), 0);
    const unchanged = mockDb.getRecord();
    assert.equal(unchanged?.status, 'pending');
    assert.equal(unchanged?.approval_email_sent_at, null);
  });

  // Test 5: Already-sent approval does not send duplicate emails
  it('5. Already-sent approval does not send duplicate emails', async () => {
    const mockDb = createMockSupabase({
      id: 'req_5',
      email: 'already-approved@example.com',
      status: 'approved',
      approved_at: '2026-09-10T10:00:00Z',
      approval_email_sent_at: '2026-09-10T10:00:00Z',
    });
    const mockResend = createMockResend();

    const result = await approveBetaUser({
      email: 'already-approved@example.com',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      supabaseClient: mockDb as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      resendClient: mockResend as any,
    });

    assert.equal(result.success, false);
    assert.equal(result.code, 'ALREADY_SENT');
    assert.equal(mockResend.sentCalls.length, 0);
    assert.equal(mockDb.getUpdateCallCount(), 0);
  });

  // Test 6: Missing RESEND_API_KEY fails safely
  it('6. Missing RESEND_API_KEY fails safely without crashing', async () => {
    delete process.env.RESEND_API_KEY;

    const mockDb = createMockSupabase({
      id: 'req_6',
      email: 'tester6@example.com',
      status: 'pending',
      approved_at: null,
      approval_email_sent_at: null,
    });

    const result = await approveBetaUser({
      email: 'tester6@example.com',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      supabaseClient: mockDb as any,
    });

    assert.equal(result.success, false);
    assert.equal(result.code, 'CONFIG_ERROR');
    assert.match(result.message, /RESEND_API_KEY/);
    assert.equal(mockDb.getUpdateCallCount(), 0);
  });

  // Test 7: Missing RESEND_FROM_EMAIL fails safely
  it('7. Missing RESEND_FROM_EMAIL fails safely with server configuration error', async () => {
    delete process.env.RESEND_FROM_EMAIL;

    const mockDb = createMockSupabase({
      id: 'req_7',
      email: 'tester7@example.com',
      status: 'pending',
      approved_at: null,
      approval_email_sent_at: null,
    });
    const mockResend = createMockResend();

    const result = await approveBetaUser({
      email: 'tester7@example.com',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      supabaseClient: mockDb as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      resendClient: mockResend as any,
    });

    assert.equal(result.success, false);
    assert.equal(result.code, 'CONFIG_ERROR');
    assert.match(result.message, /RESEND_FROM_EMAIL/);
    assert.equal(mockResend.sentCalls.length, 0);
  });

  // Test 8: Unauthorized approval request is rejected
  it('8. Unauthorized approval request is rejected (timing-safe check & route)', async () => {
    assert.equal(constantTimeCompare('secret123', 'secret123'), true);
    assert.equal(constantTimeCompare('secret123', 'wrong'), false);

    const check1 = validateAdminAuth('Bearer wrong-secret');
    assert.equal(check1.authorized, false);

    const check2 = validateAdminAuth(null);
    assert.equal(check2.authorized, false);

    const check3 = validateAdminAuth('Bearer notch-super-secret-admin-key-2026');
    assert.equal(check3.authorized, true);

    const req = new NextRequest('http://localhost:3000/api/beta/approve', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: 'Bearer invalid-token',
      },
      body: JSON.stringify({ email: 'tester@example.com' }),
    });

    const res = await POST(req);
    assert.equal(res.status, 401);
    const body = await res.json();
    assert.equal(body.success, false);
    assert.equal(body.error, 'Unauthorized.');
  });

  // Test 9: Admin secret is never returned in API responses
  it('9. Admin secret is never returned in API responses', async () => {
    const adminSecret = 'notch-super-secret-admin-key-2026';

    const unauthReq = new NextRequest('http://localhost:3000/api/beta/approve', {
      method: 'POST',
      headers: {
        authorization: 'Bearer bad-secret',
        'content-type': 'application/json',
      },
      body: JSON.stringify({ email: 'test@example.com' }),
    });
    const unauthRes = await POST(unauthReq);
    const unauthBodyStr = JSON.stringify(await unauthRes.json());
    assert.equal(unauthBodyStr.includes(adminSecret), false);

    delete process.env.BETA_ADMIN_SECRET;
    const noConfigReq = new NextRequest('http://localhost:3000/api/beta/approve', {
      method: 'POST',
      headers: {
        authorization: 'Bearer some-secret',
        'content-type': 'application/json',
      },
      body: JSON.stringify({ email: 'test@example.com' }),
    });
    const noConfigRes = await POST(noConfigReq);
    const noConfigStr = JSON.stringify(await noConfigRes.json());
    assert.equal(noConfigStr.includes(adminSecret), false);
  });

  // Test 10: /api/download redirects to the release download URL
  it('10. /api/download route redirects directly to the installer URL', async () => {
    const response = await downloadRouteGet();
    assert.equal(response.status, 307);
    const location = response.headers.get('location');
    assert.equal(location, DEFAULT_NOTCH_DOWNLOAD_URL);
  });

  // Test 11: Resend API key and secrets never appear in client bundles
  it('11. Resend API key, Admin Secret, and Supabase Service Role Key never appear in client bundles', () => {
    const clientDirs = [
      path.resolve(__dirname, '../../../components'),
      path.resolve(__dirname, '../../../app'),
    ];

    const forbiddenTokens = [
      'process.env.RESEND_API_KEY',
      'process.env.BETA_ADMIN_SECRET',
      'process.env.SUPABASE_SERVICE_ROLE_KEY',
      'RESEND_API_KEY',
      'BETA_ADMIN_SECRET',
    ];

    function checkDir(dirPath: string) {
      if (!fs.existsSync(dirPath)) return;
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);
        if (fullPath.includes(path.join('app', 'api'))) continue;

        if (entry.isDirectory()) {
          checkDir(fullPath);
        } else if (/\.(tsx|jsx|js|ts)$/.test(entry.name)) {
          const content = fs.readFileSync(fullPath, 'utf8');
          for (const token of forbiddenTokens) {
            assert.equal(
              content.includes(token),
              false,
              `Found forbidden token "${token}" in client file ${fullPath}`
            );
          }
        }
      }
    }

    for (const dir of clientDirs) {
      checkDir(dir);
    }
  });
});
