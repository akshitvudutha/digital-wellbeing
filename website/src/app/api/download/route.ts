import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export const DEFAULT_NOTCH_DOWNLOAD_URL =
  'https://github.com/akshitvudutha/digital-wellbeing/releases/download/v3.1.6/NotchSetup-3.1.6.exe';

export async function GET() {
  const downloadUrl = (process.env.NOTCH_DOWNLOAD_URL || DEFAULT_NOTCH_DOWNLOAD_URL).trim();
  return NextResponse.redirect(downloadUrl, 307);
}
