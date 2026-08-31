import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

// Required minimum version for the website to serve
const MIN_VERSION = '3.0.0';

function parseVersion(v: string): number[] {
  const match = v.match(/(\d+\.\d+\.\d+)/);
  if (!match) return [0, 0, 0];
  return match[1].split('.').map(Number);
}

function isNewer(latest: string, current: string): boolean {
  const l = parseVersion(latest);
  const c = parseVersion(current);
  for (let i = 0; i < 3; i++) {
    if (l[i] > c[i]) return true;
    if (l[i] < c[i]) return false;
  }
  return false;
}

function isNewerOrEqual(latest: string, current: string): boolean {
  if (latest === current) return true;
  const l = parseVersion(latest);
  const c = parseVersion(current);
  for (let i = 0; i < 3; i++) {
    if (l[i] > c[i]) return true;
    if (l[i] < c[i]) return false;
  }
  return true;
}

export async function GET() {
  try {
    const res = await fetch('https://api.github.com/repos/akshitvudutha/digital-wellbeing/releases', {
      headers: {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'DigitalWellbeing-Website'
      },
      next: { revalidate: 60 } // Cache for 1 minute
    });

    if (!res.ok) {
      return new NextResponse('GitHub API Error', { status: 500 });
    }

    const releases = await res.json();
    
    let bestRelease = null;
    let bestVersion = '0.0.0';

    for (const release of releases) {
      if (release.draft || release.prerelease) continue;
      const tag = release.tag_name || release.name || '';
      if (isNewer(tag, bestVersion)) {
        bestVersion = tag;
        bestRelease = release;
      }
    }

    // Safety rule: never download an older release
    if (!bestRelease || !isNewerOrEqual(bestVersion, MIN_VERSION)) {
      return new NextResponse(`
        <html>
          <body style="font-family: sans-serif; text-align: center; padding: 50px; background: #111; color: #fff;">
            <h2>Download Unavailable</h2>
            <p>The requested version of NYW (v${MIN_VERSION} or newer) is not yet published.</p>
            <p>Please wait for the developer to publish the GitHub release.</p>
          </body>
        </html>
      `, { status: 404, headers: { 'Content-Type': 'text/html' } });
    }
    
    // Find the installer asset ending in .exe
    const installerAsset = bestRelease.assets?.find((asset: any) => 
      asset.name.toLowerCase().endsWith('.exe') && 
      (asset.name.toLowerCase().includes('setup') || asset.name.toLowerCase().includes('digitalwellbeing'))
    );

    if (installerAsset && installerAsset.browser_download_url) {
      return NextResponse.redirect(installerAsset.browser_download_url);
    }

    return new NextResponse(`
      <html>
        <body style="font-family: sans-serif; text-align: center; padding: 50px; background: #111; color: #fff;">
          <h2>Download Unavailable</h2>
          <p>No valid Windows installer (.exe) was found in the latest release.</p>
        </body>
      </html>
    `, { status: 404, headers: { 'Content-Type': 'text/html' } });
    
  } catch (error) {
    console.error('Error fetching release:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}
