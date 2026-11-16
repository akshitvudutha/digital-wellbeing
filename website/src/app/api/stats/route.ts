import { NextResponse } from 'next/server';
import { siteConfig } from '@/config/site';

export const revalidate = 86400; // Cache for 24 hours

export async function GET() {
  return NextResponse.json({
    project: 'Notch — Digital Wellbeing for Windows',
    version: siteConfig.version,
    stagedVersion: siteConfig.stagedVersion,
    stage: siteConfig.stage,
    architecture: 'Local activity storage, no cloud sync, install-ID and version heartbeat',
  });
}
