# REBRAND_NOTES.md

## Brand Changes
- **Retired brands:** Digital Wellbeing, NYW (Not Your Wellbeing)
- **Final Product Brand:** Notch (Visual treatment: NOTCH)
- **Product Descriptor:** Digital Wellbeing for Windows
- **Version:** 3.1.6

## What User-Facing Surfaces Changed
1. **Desktop Application UI:**
   - Sidebar logo header now displays "NOTCH".
   - Window title dynamically displays "Notch v3.1.6".
   - Settings page descriptions reflect "Notch".
   - Update dialog title and copy changed to "Notch Update Available" / "A newer version of Notch is ready to be installed."
   - Tray icon menu action renamed to "Open Notch".
   - All protection and authentication dialogs updated to "Notch" (e.g. "This application is protected by Notch", "Enter Notch PIN", "App Blocked by Focus — Notch").
2. **Installer Metadata:**
   - Inno Setup wizard dialogs and titles display "Notch".
   - Windows shortcuts inside Start Menu, Startup, and Desktop use "Notch".
   - Output installer named `NotchSetup-3.1.6.exe`.
   - Windows Registry metadata for Apps & Features lists "Notch".
3. **Executable Metadata:**
   - Embedded `ProductName` updated to "Notch".
   - `FileDescription` set to "Notch — Digital Wellbeing for Windows".
4. **Website:**
   - Site title: "Notch — Digital Wellbeing for Windows".
   - Navbar brand: "NOTCH".
   - Footer brand: "NOTCH".
   - Canonical logo asset referenced cleanly as `/notch-logo.png`.
   - All hero, capability, philosophy, privacy, and beta registration copy updated to "Notch".
   - All screenshots updated from running application to showcase "NOTCH" branding in Dark and Light modes.
5. **Documentation:**
   - README updated with "# Notch — Digital Wellbeing for Windows".

## Technical Identifiers Intentionally Retained
To prevent breaking existing configurations, user data, or update mechanisms, the following underlying technical IDs remain unchanged:
- **Executable Name:** `DigitalWellbeing.exe` (maintains compatibility with registry paths, shortcut targets, startup tasks, and updater hooks)
- **GitHub Repository:** `akshitvudutha/digital-wellbeing` (remains active until formally changed)
- **App Data Directory/DB:** `digital_wellbeing.db` inside user AppData (`DigitalWellbeing`).
- **Python Module Imports:** Internal module structures remain under existing package namespaces.
- **Windows Toast AppID:** `DigitalWellbeing` ID retained for notification permission grouping.
- **CHANGELOG:** Historical entries retain past names for archival accuracy.
