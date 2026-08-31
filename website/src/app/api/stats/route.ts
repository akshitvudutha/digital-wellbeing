import { NextResponse } from 'next/server';
import { kv } from '@vercel/kv';

export const revalidate = 3600; // Cache for 1 hour

export async function GET() {
  try {
    // 1. Fetch GitHub Downloads
    let downloads = 0;
    try {
      const response = await fetch('https://api.github.com/repos/akshitvudutha/digital-wellbeing/releases/tags/v3.1.5', {
        headers: {
          'Accept': 'application/vnd.github.v3+json',
        },
        next: { revalidate: 3600 }
      });
      
      if (response.ok) {
        const data = await response.json();
        // Sum download counts of all assets (usually just the .exe)
        if (data.assets && Array.isArray(data.assets)) {
          downloads = data.assets.reduce((acc: number, asset: any) => acc + (asset.download_count || 0), 0);
        }
      }
    } catch (err) {
      console.error('Failed to fetch GitHub stats:', err);
      // Fail gracefully, downloads will be 0 or previous cached value
    }

    // 2. Fetch Active Users from KV (last 30 days)
    let activeInstalls = 0;
    try {
      const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
      activeInstalls = await kv.zcount('active_installs', thirtyDaysAgo, '+inf');
    } catch (err) {
      console.error('Failed to fetch KV stats:', err);
    }

    return NextResponse.json({
      downloads,
      activeInstalls,
      version: 'v3.1.5'
    });
  } catch (error) {
    console.error('Stats API error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
