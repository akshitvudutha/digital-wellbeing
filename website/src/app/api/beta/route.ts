import { NextRequest, NextResponse } from 'next/server';
import { processBetaRequest, BetaAccessPayload } from '@/lib/beta/service';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json()) as BetaAccessPayload;
    
    // Extract client IP for sliding window rate limiting
    const forwardedFor = req.headers.get('x-forwarded-for');
    const clientIp = forwardedFor ? forwardedFor.split(',')[0].trim() : '127.0.0.1';

    const result = await processBetaRequest(body, clientIp);

    if (!result.success) {
      const status = result.code === 'RATE_LIMITED' ? 429 : 400;
      return NextResponse.json(result, { status });
    }

    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    console.error('Beta route exception:', error);
    return NextResponse.json(
      {
        success: false,
        message: 'An unexpected error occurred. Please try again shortly.',
      },
      { status: 500 }
    );
  }
}
