!include "MUI2.nsh"

Name "AI Assistant"
OutFile "AI_Assistant_Setup.exe"
InstallDir "$PROGRAMFILES\AI Assistant"
InstallDirRegKey HKLM "Software\AI Assistant" "Install_Dir"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "AI Assistant"
  SectionIn RO
  
  SetOutPath "$INSTDIR"
  File /r "dist\win-unpacked\*.*"
  
  WriteRegStr HKLM "Software\AI Assistant" "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "DisplayName" "AI Assistant"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "DisplayIcon" "$INSTDIR\AI Assistant.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "Publisher" "AI Assistant Team"
  
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
  CreateShortcut "$SMPROGRAMS\AI Assistant.lnk" "$INSTDIR\AI Assistant.exe"
  CreateShortcut "$DESKTOP\AI Assistant.lnk" "$INSTDIR\AI Assistant.exe"
SectionEnd

Section "Start Menu Shortcut"
  CreateShortcut "$SMPROGRAMS\AI Assistant.lnk" "$INSTDIR\AI Assistant.exe"
SectionEnd

Section "Auto Start"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "AI Assistant" "$INSTDIR\AI Assistant.exe --minimized"
SectionEnd

Section "Uninstall"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant"
  DeleteRegKey HKLM "Software\AI Assistant"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "AI Assistant"
  
  Delete "$SMPROGRAMS\AI Assistant.lnk"
  Delete "$DESKTOP\AI Assistant.lnk"
  
  RMDir /r "$INSTDIR"
SectionEnd
