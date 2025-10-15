; NetPulse Windows Installer Script (Inno Setup)
[Setup]
AppName=NetPulse
AppVersion=1.0.1
AppPublisher=NetPulse
DefaultDirName={pf}\NetPulse
DefaultGroupName=NetPulse
OutputBaseFilename=NetPulse_Setup_v1.0.1
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern
SetupIconFile=icons\netpulse.ico
Uninstallable=yes

[Files]
Source: "dist\NetPulse.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.txt"; DestDir: "{app}"; Flags: isreadme
Source: "icons\netpulse.ico"; DestDir: "{app}"

[Icons]
Name: "{autoprograms}\NetPulse"; Filename: "{app}\NetPulse.exe"; IconFilename: "{app}\netpulse.ico"
Name: "{autodesktop}\NetPulse"; Filename: "{app}\NetPulse.exe"; IconFilename: "{app}\netpulse.ico"

[Run]
Filename: "{app}\NetPulse.exe"; Description: "Launch NetPulse"; Flags: nowait postinstall skipifsilent
