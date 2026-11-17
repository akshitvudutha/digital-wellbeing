import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const DEFAULT_NOTCH_DOWNLOAD_URL =
  'https://github.com/akshitvudutha/digital-wellbeing/releases/download/v3.6.4/NotchSetup-3.6.4.exe';

export async function GET() {
  const downloadUrl = (process.env.NOTCH_DOWNLOAD_URL || DEFAULT_NOTCH_DOWNLOAD_URL).trim();
  return NextResponse.redirect(downloadUrl, 307);
}
