import { NextResponse } from 'next/server';
import { kv } from '@vercel/kv';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { installId, version } = body;

    if (!installId || typeof installId !== 'string') {
      return NextResponse.json({ error: 'Invalid installId' }, { status: 400 });
    }

    // Rate limiting or simple sanity check: max string length
    if (installId.length > 64) {
      return NextResponse.json({ error: 'installId too long' }, { status: 400 });
    }

    const now = Date.now();
    
    // ZADD adds or updates the score (timestamp) for the installId
    await kv.zadd('active_installs', { score: now, member: installId });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Heartbeat error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
