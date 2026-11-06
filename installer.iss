#define AppName "PDF Stüdyo"
#define AppExe "PDF Studyo.exe"
#define AppVersion "1.0.2"

[Setup]
AppId={{A8E5C0D2-7B41-4E9A-9F3D-5C2B8E1F4A70}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Yusuf Cihan
AppPublisherURL=https://github.com/Yusufcihan1/pdf-studyo
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=PDF Studyo Kurulum
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExe}
LicenseFile=LICENSE
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\PDF Studyo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} Kaldır"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; PDF dosyalarının "Birlikte aç" listesine eklenir (varsayılan programı değiştirmez).
Root: HKA; Subkey: "Software\Classes\PDFStudyo.pdf"; ValueType: string; ValueName: ""; ValueData: "PDF belgesi"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\PDFStudyo.pdf\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"
Root: HKA; Subkey: "Software\Classes\PDFStudyo.pdf\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "PDFStudyo.pdf"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\{#AppName}\pencere"
