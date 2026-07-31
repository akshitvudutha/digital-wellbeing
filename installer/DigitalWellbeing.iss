; Inno Setup Script for Digital Wellbeing
; Ref: https://jrsoftware.org/isinfo.php

[Setup]
SourceDir=..
AppName=Digital Wellbeing
AppVersion={#MyAppVersion}
AppPublisher=Akshit Vudutha
AppPublisherURL=https://github.com/akshitlabs/digitalwellbeing
AppSupportURL=https://github.com/akshitlabs/digitalwellbeing/issues
AppUpdatesURL=https://github.com/akshitlabs/digitalwellbeing/releases
DefaultDirName={autopf}\DigitalWellbeing
DisableDirPage=yes
DefaultGroupName=Digital Wellbeing
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=DigitalWellbeingSetup
SetupIconFile=assets\icons\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany=Akshit Vudutha
VersionInfoDescription=Digital Wellbeing Setup Installer
VersionInfoCopyright=Copyright (C) 2026 Akshit Vudutha. All rights reserved.
VersionInfoProductName=Digital Wellbeing Platform
VersionInfoProductVersion={#MyAppVersion}
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Start Digital Wellbeing automatically when Windows boots"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "dist\DigitalWellbeing\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Digital Wellbeing"; Filename: "{app}\DigitalWellbeing.exe"; IconFilename: "{app}\assets\icons\app_icon.ico"
Name: "{userdesktop}\Digital Wellbeing"; Filename: "{app}\DigitalWellbeing.exe"; IconFilename: "{app}\assets\icons\app_icon.ico"; Tasks: desktopicon
Name: "{userstartup}\Digital Wellbeing"; Filename: "{app}\DigitalWellbeing.exe"; Parameters: "--background"; IconFilename: "{app}\assets\icons\app_icon.ico"; Tasks: startup

[Run]
Filename: "{app}\DigitalWellbeing.exe"; Description: "{cm:LaunchProgram,Digital Wellbeing}"; Flags: nowait postinstall skipifsilent
