import { NextResponse } from 'next/server';

export const runtime = 'edge';

export async function GET() {
  try {
    const res = await fetch('https://api.github.com/repos/akshitvudutha/digital-wellbeing/releases/latest', {
      headers: {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'DigitalWellbeing-Website'
      },
      next: { revalidate: 300 } // Cache for 5 minutes
    });

    if (!res.ok) {
      // Fallback to the releases page if API fails
      return NextResponse.redirect('https://github.com/akshitvudutha/digital-wellbeing/releases/latest');
    }

    const data = await res.json();
    
    // Find the installer asset ending in .exe
    const installerAsset = data.assets?.find((asset: any) => 
      asset.name.toLowerCase().endsWith('.exe') && 
      (asset.name.toLowerCase().includes('setup') || asset.name.toLowerCase().includes('digitalwellbeing'))
    );

    if (installerAsset && installerAsset.browser_download_url) {
      return NextResponse.redirect(installerAsset.browser_download_url);
    }

    // Fallback if no valid asset found
    return NextResponse.redirect('https://github.com/akshitvudutha/digital-wellbeing/releases/latest');
    
  } catch (error) {
    console.error('Error fetching release:', error);
    return NextResponse.redirect('https://github.com/akshitvudutha/digital-wellbeing/releases/latest');
  }
}
