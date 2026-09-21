; ============================================================
; installer.iss — Instalador do SentinelAI
; Abra este arquivo no Inno Setup (gratuito: https://jrsoftware.org/isdl.php)
; e clique em "Compile" (ou pressione F9/Ctrl+F9).
; Gera: Output\SentinelAI_Setup.exe
;
; Pré-requisito: já ter rodado build_exe.bat, para existir
; dist\SentinelAI.exe na raiz do projeto.
; ============================================================

#define MyAppName "SentinelAI"
#define MyAppVersion "4.0"
#define MyAppPublisher "CiberSeg"
#define MyAppExeName "SentinelAI.exe"

[Setup]
AppId={{B37F5C4A-8B21-4E6A-9C1B-2F0A1D4E9A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=Output
OutputBaseFilename=SentinelAI_Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
PrivilegesRequired=lowest

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: checkedonce

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName} agora"; Flags: nowait postinstall skipifsilent
