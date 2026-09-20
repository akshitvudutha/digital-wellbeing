; Inno Setup Script for Digital Wellbeing
; Ref: https://jrsoftware.org/isinfo.php

[Setup]
SourceDir=..
AppId=Digital Wellbeing
AppName=Notch
AppVersion={#MyAppVersion}
AppPublisher=Akshit Vudutha
AppPublisherURL=https://github.com/akshitlabs/digitalwellbeing
AppSupportURL=https://github.com/akshitlabs/digitalwellbeing/issues
AppUpdatesURL=https://github.com/akshitlabs/digitalwellbeing/releases
DefaultDirName={autopf}\DigitalWellbeing
DisableDirPage=yes
DefaultGroupName=Notch
DisableProgramGroupPage=yes
UsePreviousGroup=no
OutputDir=dist
OutputBaseFilename=NotchSetup
SetupIconFile=assets\icons\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany=Akshit Vudutha
VersionInfoDescription=Notch Setup Installer
VersionInfoCopyright=Copyright (C) 2026 Akshit Vudutha. All rights reserved.
VersionInfoProductName=Notch
VersionInfoProductVersion={#MyAppVersion}
CloseApplications=yes
UninstallDisplayIcon={app}\DigitalWellbeing.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Start Notch automatically when Windows boots"; GroupDescription: "Startup:"; Flags: unchecked

[InstallDelete]
; Clean up legacy shortcuts from v2.5.2 and earlier
Type: files; Name: "{userprograms}\Digital Wellbeing\Digital Wellbeing.lnk"
Type: dirifempty; Name: "{userprograms}\Digital Wellbeing"
Type: files; Name: "{commonprograms}\Digital Wellbeing\Digital Wellbeing.lnk"
Type: dirifempty; Name: "{commonprograms}\Digital Wellbeing"
Type: files; Name: "{userdesktop}\Digital Wellbeing.lnk"
Type: files; Name: "{commondesktop}\Digital Wellbeing.lnk"
Type: files; Name: "{userstartup}\Digital Wellbeing.lnk"
Type: files; Name: "{commonstartup}\Digital Wellbeing.lnk"
; Clean up previous NYW shortcuts
Type: files; Name: "{userprograms}\NYW\NYW.lnk"
Type: files; Name: "{userprograms}\NYW\Notch.lnk"
Type: dirifempty; Name: "{userprograms}\NYW"
Type: files; Name: "{userdesktop}\NYW.lnk"
Type: files; Name: "{userstartup}\NYW.lnk"

[Files]
Source: "dist\DigitalWellbeing\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Notch"; Filename: "{app}\DigitalWellbeing.exe"; AppUserModelID: "AkshitVudutha.DigitalWellbeing.App.2"
Name: "{userdesktop}\Notch"; Filename: "{app}\DigitalWellbeing.exe"; Tasks: desktopicon; AppUserModelID: "AkshitVudutha.DigitalWellbeing.App.2"
Name: "{userstartup}\Notch"; Filename: "{app}\DigitalWellbeing.exe"; Parameters: "--background"; Tasks: startup; AppUserModelID: "AkshitVudutha.DigitalWellbeing.App.2"

[Registry]
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\AkshitVudutha.DigitalWellbeing.App.2"; ValueType: string; ValueName: "DisplayName"; ValueData: "Notch"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\AkshitVudutha.DigitalWellbeing.App.2"; ValueType: string; ValueName: "IconUri"; ValueData: "{app}\assets\icons\app_icon.ico"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\AkshitVudutha.DigitalWellbeing.App.2"; ValueType: dword; ValueName: "ShowInSettings"; ValueData: 1; Flags: uninsdeletekey

[Run]
Filename: "{app}\DigitalWellbeing.exe"; Description: "{cm:LaunchProgram,Notch}"; Flags: nowait postinstall skipifsilent
