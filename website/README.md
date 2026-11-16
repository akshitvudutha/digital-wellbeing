# Notch website

The website is the independent Next.js application for Notch product information, privacy details, screenshots, and distribution links. Keep feature claims aligned with the desktop code and tests. Do not change the configured release version or download destination without an approved release update.

## Local development

```powershell
npm install
npm run dev
```

Open `http://localhost:3000` in a browser.

## Quality checks

Run these from the `website/` directory:

```powershell
npm run lint
npm test
npx tsc --noEmit
npm run build
```

The layout uses a system font stack, so production builds do not need to fetch fonts from an external service.

## Source structure

- `src/app/` contains the homepage, shared layout, and download/statistics routes.
- `src/components/` contains shared layout and interactive capability components.
- `src/config/site.ts` contains public site metadata and links.
- `src/__tests__/` contains website unit tests.
- `public/images/app/` contains desktop application screenshots.
