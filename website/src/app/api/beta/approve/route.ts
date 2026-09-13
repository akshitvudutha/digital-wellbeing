import { NextRequest, NextResponse } from 'next/server';
import { validateAdminAuth } from '@/lib/auth/admin';
import { approveBetaUser } from '@/lib/beta/approval';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  try {
    // 1. Authenticate admin using timing-safe comparison
    const authHeader = req.headers.get('authorization') || req.headers.get('x-admin-secret');
    const authCheck = validateAdminAuth(authHeader);

    if (!authCheck.authorized) {
      if (authCheck.error === 'CONFIG_MISSING') {
        return NextResponse.json(
          {
            success: false,
            error: 'Server authentication is not configured.',
          },
          { status: 500 }
        );
      }

      return NextResponse.json(
        {
          success: false,
          error: 'Unauthorized.',
        },
        { status: 401 }
      );
    }

    // 2. Parse request payload
    let body: { email?: string; id?: string };
    try {
      body = await req.json();
    } catch {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid JSON request body.',
        },
        { status: 400 }
      );
    }

    if (!body || (!body.email && !body.id)) {
      return NextResponse.json(
        {
          success: false,
          error: 'Missing required field: "email" or "id" must be provided.',
        },
        { status: 400 }
      );
    }

    // 3. Process beta approval and email dispatch
    const result = await approveBetaUser({
      email: body.email,
      id: body.id,
    });

    if (!result.success) {
      let status = 400;
      switch (result.code) {
        case 'NOT_FOUND':
          status = 404;
          break;
        case 'ALREADY_SENT':
          status = 409;
          break;
        case 'CONFIG_ERROR':
        case 'DB_ERROR':
          status = 500;
          break;
        case 'EMAIL_FAILED':
          status = 502;
          break;
        default:
          status = 400;
      }

      return NextResponse.json(result, { status });
    }

    return NextResponse.json(result, { status: 200 });
  } catch (error: unknown) {
    console.error('[Beta Approval API Route Error]:', error instanceof Error ? error.message : 'Unknown');
    return NextResponse.json(
      {
        success: false,
        error: 'An unexpected server error occurred.',
      },
      { status: 500 }
    );
  }
}
