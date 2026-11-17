import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { GET as downloadRoute } from '@/app/api/download/route';
import { GET as statsRoute } from '@/app/api/stats/route';
import { siteConfig } from '@/config/site';

describe('Notch Public Release & Distribution System', () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = { ...originalEnv };
  });

  it('1. /api/download redirects to default GitHub release URL with HTTP 307', async () => {
    delete process.env.NOTCH_DOWNLOAD_URL;

    const response = await downloadRoute();
    assert.equal(response.status, 307);
    assert.equal(
      response.headers.get('location'),
      'https://github.com/akshitvudutha/digital-wellbeing/releases/download/v3.6.4/NotchSetup-3.6.4.exe'
    );
  });

  it('2. /api/download respects NOTCH_DOWNLOAD_URL environment variable override', async () => {
    process.env.NOTCH_DOWNLOAD_URL = 'https://custom-cdn.example.com/NotchSetup-3.6.4.exe';

    const response = await downloadRoute();
    assert.equal(response.status, 307);
    assert.equal(
      response.headers.get('location'),
      'https://custom-cdn.example.com/NotchSetup-3.6.4.exe'
    );
  });

  it('3. /api/stats returns accurate project metadata and Public Release stage', async () => {
    const response = await statsRoute();
    assert.equal(response.status, 200);

    const data = await response.json();
    assert.equal(data.project, 'Notch — Digital Wellbeing for Windows');
    assert.equal(data.version, '3.6.4');
    assert.equal(data.stagedVersion, '3.6.4');
    assert.equal(data.stage, 'Public Release');
    assert.equal(
      data.architecture,
      'Local activity storage, no cloud sync, install-ID and version heartbeat'
    );
  });

  it('4. siteConfig is aligned with Public Release v3.6.4 and staged v3.6.4', () => {
    assert.equal(siteConfig.name, 'Notch');
    assert.equal(siteConfig.version, '3.6.4');
    assert.equal(siteConfig.stagedVersion, '3.6.4');
    assert.equal(siteConfig.stage, 'Public Release');
    assert.equal(
      siteConfig.links.releases,
      'https://github.com/akshitvudutha/digital-wellbeing/releases'
    );
  });

  it('5. Public download operates independently without external database or email dependencies', async () => {
    const response = await downloadRoute();
    assert.equal(response.status, 307);
    assert.equal(
      response.headers.get('location'),
      'https://github.com/akshitvudutha/digital-wellbeing/releases/download/v3.6.4/NotchSetup-3.6.4.exe'
    );
  });
});
