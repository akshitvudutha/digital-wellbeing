# REBRAND_NOTES.md

## Brand Changes
- **Old brand:** Digital Wellbeing
- **New brand:** NYW — Not Your Wellbeing
- **Descriptor:** Digital wellbeing for Windows
- **Tagline:** Your time. Your rules.

## What User-Facing Surfaces Changed
1. **Desktop Application UI:**
   - Sidebar logo label now reads "NYW".
   - Settings page descriptions reflect "NYW".
   - Update dialog title changed to "NYW Update Available".
   - Tray icon menu action renamed to "Open Not Your Wellbeing".
2. **Installer Metadata:**
   - Inno Setup wizard dialogs and titles display "NYW" and "Not Your Wellbeing".
   - Windows shortcuts inside start menu and desktop use "NYW".
   - Windows Registry metadata for Apps & Features lists "Not Your Wellbeing".
3. **Executable Metadata:**
   - Embedded `ProductName` and `FileDescription` updated to "Not Your Wellbeing".
4. **Website:**
   - SEO metadata, Hero Section, Feature Sections, and Download Fallback updated to "NYW" and the new tagline.
   - All references to "Digital Wellbeing" were replaced appropriately to fit the new context.
5. **Documentation:**
   - README updated with the new branding.

## Technical Identifiers Intentionally Retained
To prevent breaking existing configurations, data, or update mechanisms, the following underlying technical IDs remain unchanged:
- **Executable Name:** `DigitalWellbeing.exe` (maintains compatibility with registry paths, shortcut targets, startup tasks, and updater hooks)
- **Installer Filename:** `DigitalWellbeingSetup-2.5.2.exe` (keeps Vercel fallback URL checks and updater string matching intact)
- **GitHub Repository:** `akshitvudutha/digital-wellbeing` (remains active until formally changed)
- **App Data Directory/DB:** `digital_wellbeing.db` inside `.digital_wellbeing` folder.
- **Python Module Imports:** Internal module structures remain under `digitalwellbeing` namespaces.
- **Windows Toast AppID:** `DigitalWellbeing` ID retained for notification permission grouping.
- **CHANGELOG:** Historical entries retain "Digital Wellbeing" for accuracy.

## Future Cleanup Recommendations
- **Logo Replacement:** Current icon assets (`app_icon.ico`, `app_logo.png`) have been retained. In the future, new logo assets should be swapped at the same paths to safely replace them without touching UI code.
- **Repository Rename:** Once all clients are on v2.5.2 or greater (which uses the `/releases` endpoint search instead of hardcoded github repo paths if changed in config), the repository can safely be renamed on GitHub.
- **Installer Filename Rename:** The installer filename can be safely renamed in a future major version bump (e.g. v3.0) where website API `route.ts` and `core/updater.py` logic are synchronously updated to seek `NYWSetup.exe`.
