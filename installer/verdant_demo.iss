; Verdant Demo Installer Script
#define MyAppName "Verdant Demo"
#if GetEnv('GITHUB_REF_NAME') != ""
  #define MyAppVersion GetEnv('GITHUB_REF_NAME')
#else
  #define MyAppVersion "v0.0.0"
#endif
#define MyAppPublisher "Verdant Leaf"
#define MyAppURL "https://kaankutluturk.github.io/verdant/"
#define MyAppExeName "VerdantApp.exe"
#define UpdaterExeName "VerdantUpdater.exe"

[Setup]
AppId={{9A7B4F0E-19F5-49E1-9B9D-8E8B0D9F1D10}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\Verdant Demo
DefaultGroupName=Verdant Demo
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=verdant-demo-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
#ifexist "{#SourcePath}\..\assets\icon\verdant.ico"
SetupIconFile={#SourcePath}\..\assets\icon\verdant.ico
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#SourcePath}\..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourcePath}\..\presets.json"; DestDir: "{app}"; Flags: ignoreversion
#ifexist "{#SourcePath}\..\dist\{#UpdaterExeName}"
Source: "{#SourcePath}\..\dist\{#UpdaterExeName}"; DestDir: "{app}"; Flags: ignoreversion
#endif

[Icons]
Name: "{autoprograms}\Verdant Demo"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Verdant Demo"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Verdant Demo"; Flags: nowait postinstall skipifsilent

[InstallDelete]
Type: files; Name: "{app}\version.txt"

[Code]
var
  VerFile: string;
  ChanFile: string;

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
    ChanFile := ExpandConstant('{app}') + '\channel.txt';
    SaveStringToFile(ChanFile, 'demo', False);
  end;
end; 