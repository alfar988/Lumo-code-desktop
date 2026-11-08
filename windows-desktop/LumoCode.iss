#define MyAppName "Lumo Code"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Alfarz"
#define MyAppURL "https://github.com/alfar988/Lumo-code"
#define BootstrapExe "..\dist\LumoBootstrap.exe"

[Setup]
AppId={{8A0D927C-3A80-4B26-AAD5-7B28B6A2DDA1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\LumoCode
DefaultGroupName=Lumo Code
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
OutputDir=..\dist
OutputBaseFilename=LumoCode-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\LumoBootstrap.exe
CloseApplications=no
SetupLogging=yes

[Files]
Source: "{#BootstrapExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Lumo Code"; Filename: "{app}\LumoBootstrap.exe"; Parameters: "--launch"; WorkingDir: "{userprofile}\workspace"
Name: "{autodesktop}\Lumo Code"; Filename: "{app}\LumoBootstrap.exe"; Parameters: "--launch"; WorkingDir: "{userprofile}\workspace"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\LumoBootstrap.exe"; Parameters: "--install-and-launch"; WorkingDir: "{app}"; Description: "Install and launch Lumo Code"; Flags: postinstall nowait skipifsilent
