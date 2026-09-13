import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  return new NextResponse(
    JSON.stringify({
      status: 'beta_only',
      message: 'Public downloads are paused. Notch is currently in a controlled Beta phase.',
      beta_url: 'https://notyourwellbeing.vercel.app/#beta',
    }),
    {
      status: 410,
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );
}

