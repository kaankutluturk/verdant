; Verdant Installer Script
#define MyAppName "Verdant"
#define MyAppVersion "{#GetEnv("GITHUB_REF_NAME")}"
#define MyAppPublisher "Verdant Leaf"
#define MyAppURL "https://kaankutluturk.github.io/verdant/"
#define MyAppExeName "VerdantApp.exe"
#define UpdaterExeName "VerdantUpdater.exe"

; Resolve repository root consistently in CI and locally
#define _WS "{#GetEnv('GITHUB_WORKSPACE')}"
#if _WS != ""
  #define RootPath "{#_WS}"
#else
  #define RootPath "{#SourcePath}\.."
#endif

[Setup]
AppId={{C8ED37B1-0F3D-4E0B-9B1E-2C7B0E0F47E1}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\Verdant
DefaultGroupName=Verdant
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir={#RootPath}\installer\Output
OutputBaseFilename=verdant-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
#ifexist "{#RootPath}\assets\icon\verdant.ico"
SetupIconFile={#RootPath}\assets\icon\verdant.ico
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#RootPath}\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#RootPath}\presets.json"; DestDir: "{app}"; Flags: ignoreversion
#ifexist "{#RootPath}\dist\{#UpdaterExeName}"
Source: "{#RootPath}\dist\{#UpdaterExeName}"; DestDir: "{app}"; Flags: ignoreversion
#endif

[Icons]
Name: "{autoprograms}\Verdant"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Verdant"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Verdant"; Flags: nowait postinstall skipifsilent

[InstallDelete]
Type: files; Name: "{app}\version.txt"

[Code]
var
  VerFile: string;

function GetVersionTag(): string;
begin
  if GetEnv('GITHUB_REF_NAME') <> '' then
    Result := GetEnv('GITHUB_REF_NAME')
  else
    Result := '{#MyAppVersion}';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    VerFile := ExpandConstant('{app}') + '\version.txt';
    SaveStringToFile(VerFile, GetVersionTag(), False);
  end;
end; 