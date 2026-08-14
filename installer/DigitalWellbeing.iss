; Inno Setup Script for Digital Wellbeing
; Ref: https://jrsoftware.org/isinfo.php

[Setup]
SourceDir=..
AppName=NYW
AppVersion={#MyAppVersion}
AppPublisher=Akshit Vudutha
AppPublisherURL=https://github.com/akshitlabs/digitalwellbeing
AppSupportURL=https://github.com/akshitlabs/digitalwellbeing/issues
AppUpdatesURL=https://github.com/akshitlabs/digitalwellbeing/releases
DefaultDirName={autopf}\DigitalWellbeing
DisableDirPage=yes
DefaultGroupName=NYW
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=DigitalWellbeingSetup
SetupIconFile=assets\icons\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany=Akshit Vudutha
VersionInfoDescription=Not Your Wellbeing Setup Installer
VersionInfoCopyright=Copyright (C) 2026 Akshit Vudutha. All rights reserved.
VersionInfoProductName=Not Your Wellbeing for Windows
VersionInfoProductVersion={#MyAppVersion}
CloseApplications=yes
UninstallDisplayIcon={app}\DigitalWellbeing.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Start NYW automatically when Windows boots"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "dist\DigitalWellbeing\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NYW"; Filename: "{app}\DigitalWellbeing.exe"
Name: "{userdesktop}\NYW"; Filename: "{app}\DigitalWellbeing.exe"; Tasks: desktopicon
Name: "{userstartup}\NYW"; Filename: "{app}\DigitalWellbeing.exe"; Parameters: "--background"; Tasks: startup

[Run]
Filename: "{app}\DigitalWellbeing.exe"; Description: "{cm:LaunchProgram,NYW}"; Flags: nowait postinstall skipifsilent
