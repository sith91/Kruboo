; AI Assistant Windows Installer
; NSIS Script for creating professional Windows installer

Unicode true
ManifestDPIAware true

; Include Modern UI
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

; -------------------------------
; BASIC INSTALLER CONFIGURATION
; -------------------------------

Name "AI Assistant"
Caption "AI Assistant Setup"
BrandingText "AI Assistant - Privacy-First AI Assistant"

; Version information
!define VERSION "1.0.0"
!define VERSION_BUILD "100"
!define PUBLISHER "AI Assistant Team"
!define WEB_SITE "https://github.com/your-repo/ai-assistant"
!define SUPPORT_URL "https://github.com/your-repo/ai-assistant/issues"

; File names
OutFile "..\dist\windows\AI_Assistant_Setup_${VERSION}.exe"
InstallDir "$PROGRAMFILES64\AI Assistant"
InstallDirRegKey HKLM "Software\AI Assistant" "Install_Dir"

; Request execution level for Windows Vista and above
RequestExecutionLevel admin

; Compression
SetCompressor /SOLID lzma
SetCompressorDictSize 64

; -------------------------------
; MODERN UI CONFIGURATION
; -------------------------------

; Interface configuration
!define MUI_ABORTWARNING
!define MUI_ICON "..\client\desktop\build\icon.ico"
!define MUI_UNICON "..\client\desktop\build\icon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "..\installers\assets\wizard.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "..\installers\assets\wizard.bmp"

; Welcome page
!define MUI_WELCOMEPAGE_TITLE "Welcome to AI Assistant Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of AI Assistant.$\r$\n$\r$\nAI Assistant is a privacy-first, voice-controlled AI assistant that lives on your desktop.$\r$\n$\r$\nClick Next to continue."

!insertmacro MUI_PAGE_WELCOME

; License page
!define MUI_LICENSEPAGE_HEADER_TEXT "License Agreement"
!define MUI_LICENSEPAGE_TEXT_TOP "Please read the following license agreement carefully."
!define MUI_LICENSEPAGE_BUTTON "&Agree"
!define MUI_LICENSEPAGE_TEXT_BOTTOM "Press Page Down to see the rest of the agreement."

!insertmacro MUI_PAGE_LICENSE "..\LICENSE"

; Components page
!define MUI_COMPONENTSPAGE_TEXT_TOP "Select the components you want to install. Click Next to continue."
!insertmacro MUI_PAGE_COMPONENTS

; Directory page
!define MUI_DIRECTORYPAGE_TEXT_TOP "Setup will install AI Assistant in the following folder. To install in a different folder, click Browse and select another folder. Click Next to continue."
!insertmacro MUI_PAGE_DIRECTORY

; Start Menu folder page
Var StartMenuFolder
!define MUI_STARTMENUPAGE_NODISABLE
!define MUI_STARTMENUPAGE_DEFAULTFOLDER "AI Assistant"
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKLM"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\AI Assistant"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"

!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder

; Installation page
!insertmacro MUI_PAGE_INSTFILES

; Finish page
!define MUI_FINISHPAGE_TITLE "Completing AI Assistant Setup"
!define MUI_FINISHPAGE_TEXT "AI Assistant has been installed on your computer.$\r$\n$\r$\nThe application will start automatically and appear in your system tray. Use the system tray icon or press Ctrl+Shift+A to open the main window."
!define MUI_FINISHPAGE_RUN "$INSTDIR\AI Assistant.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Run AI Assistant now"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.txt"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "View README file"
!define MUI_FINISHPAGE_LINK "Visit AI Assistant website"
!define MUI_FINISHPAGE_LINK_LOCATION "${WEB_SITE}"
!define MUI_FINISHPAGE_NOREBOOTSUPPORT

!insertmacro MUI_PAGE_FINISH

; -------------------------------
; UNINSTALLER PAGES
; -------------------------------

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; -------------------------------
; LANGUAGES
; -------------------------------

!insertmacro MUI_LANGUAGE "English"

; -------------------------------
; INSTALLER SECTIONS
; -------------------------------

Section "AI Assistant (required)" SecMain
  SectionIn RO
  
  SetOutPath "$INSTDIR"
  
  ; Main application files
  File /r "..\client\desktop\dist\win-unpacked\*.*"
  
  ; Create README file
  FileOpen $0 "$INSTDIR\README.txt" w
  FileWrite $0 "AI Assistant - Quick Start Guide$\r$\n"
  FileWrite $0 "================================$\r$\n$\r$\n"
  FileWrite $0 "Welcome to AI Assistant!$\r$\n$\r$\n"
  FileWrite $0 "Features:$\r$\n"
  FileWrite $0 "- Voice-controlled AI assistant$\r$\n"
  FileWrite $0 "- Privacy-first design$\r$\n"
  FileWrite $0 "- System integration$\r$\n"
  FileWrite $0 "- Cross-platform support$\r$\n$\r$\n"
  FileWrite $0 "Getting Started:$\r$\n"
  FileWrite $0 "1. The app runs from system tray (look for the AI icon)$\r$\n"
  FileWrite $0 "2. Use Ctrl+Shift+A to open the main window$\r$\n"
  FileWrite $0 "3. Double-click the floating orb to start voice commands$\r$\n"
  FileWrite $0 "4. Configure AI API keys in Settings for full functionality$\r$\n$\r$\n"
  FileWrite $0 "Support:$\r$\n"
  FileWrite $0 "Visit ${WEB_SITE} for documentation and support.$\r$\n"
  FileClose $0
  
  ; Store installation directory in registry
  WriteRegStr HKLM "Software\AI Assistant" "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM "Software\AI Assistant" "Version" "${VERSION}"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
  ; Add uninstall information to registry
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "DisplayName" "AI Assistant"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "DisplayIcon" "$INSTDIR\AI Assistant.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "Publisher" "${PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "Version" "${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "VersionMajor" "1"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "VersionMinor" "0"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "HelpLink" "${SUPPORT_URL}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "URLInfoAbout" "${WEB_SITE}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "NoRepair" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "EstimatedSize" 314572  ; 300MB in KB
  
SectionEnd

Section "Start Menu Shortcuts" SecStartMenu
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    
  CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
  CreateShortcut "$SMPROGRAMS\$StartMenuFolder\AI Assistant.lnk" "$INSTDIR\AI Assistant.exe"
  CreateShortcut "$SMPROGRAMS\$StartMenuFolder\Uninstall AI Assistant.lnk" "$INSTDIR\uninstall.exe"
  CreateShortcut "$SMPROGRAMS\$StartMenuFolder\README.lnk" "$INSTDIR\README.txt"
  
  !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

Section "Desktop Shortcut" SecDesktop
  CreateShortcut "$DESKTOP\AI Assistant.lnk" "$INSTDIR\AI Assistant.exe"
SectionEnd

Section "Quick Launch Shortcut" SecQuickLaunch
  CreateShortcut "$QUICKLAUNCH\AI Assistant.lnk" "$INSTDIR\AI Assistant.exe"
SectionEnd

Section "Auto Start with Windows" SecAutoStart
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "AI Assistant" "$INSTDIR\AI Assistant.exe --minimized"
SectionEnd

Section "File Associations" SecFileAssoc
  ; Associate with custom file types if needed
  ; WriteRegStr HKCR ".aiassistant" "" "AI Assistant.File"
  ; WriteRegStr HKCR "AI Assistant.File" "" "AI Assistant File"
  ; WriteRegStr HKCR "AI Assistant.File\DefaultIcon" "" "$INSTDIR\AI Assistant.exe,0"
  ; WriteRegStr HKCR "AI Assistant.File\shell\open\command" "" '"$INSTDIR\AI Assistant.exe" "%1"'
SectionEnd

; -------------------------------
; SECTION DESCRIPTIONS
; -------------------------------

LangString DESC_SecMain ${LANG_ENGLISH} "Core AI Assistant application files (required)."
LangString DESC_SecStartMenu ${LANG_ENGLISH} "Create Start Menu shortcuts for easy access."
LangString DESC_SecDesktop ${LANG_ENGLISH} "Create a desktop shortcut for quick launching."
LangString DESC_SecQuickLaunch ${LANG_ENGLISH} "Create a Quick Launch toolbar shortcut."
LangString DESC_SecAutoStart ${LANG_ENGLISH} "Automatically start AI Assistant when you log into Windows."
LangString DESC_SecFileAssoc ${LANG_ENGLISH} "Associate AI Assistant with relevant file types."

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SecMain)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} $(DESC_SecStartMenu)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} $(DESC_SecDesktop)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecQuickLaunch} $(DESC_SecQuickLaunch)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecAutoStart} $(DESC_SecAutoStart)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecFileAssoc} $(DESC_SecFileAssoc)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; -------------------------------
; INSTALLER FUNCTIONS
; -------------------------------

Function .onInit
  ; Check if already installed
  ReadRegStr $R0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant" "UninstallString"
  StrCmp $R0 "" done
  
  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
    "AI Assistant is already installed. $\n$\nClick `OK` to remove the previous version or `Cancel` to cancel this upgrade." \
    /SD IDOK \
    IDOK uninst
  Abort
  
  ; Run the uninstaller
  uninst:
    ClearErrors
    ExecWait '$R0 _?=$INSTDIR'
    
    IfErrors no_remove_uninstaller
    Goto done
    
  no_remove_uninstaller:
    MessageBox MB_OK|MB_ICONSTOP "Unable to completely remove the previous installation. Please manually uninstall AI Assistant first." /SD IDOK
    Abort
  
  done:
FunctionEnd

Function .onInstSuccess
  ; Optional: Launch the application after installation
  ; If the user checked "Run AI Assistant now" on the finish page, it will run automatically
FunctionEnd

; -------------------------------
; UNINSTALLER SECTION
; -------------------------------

Section "Uninstall"
  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI Assistant"
  DeleteRegKey HKLM "Software\AI Assistant"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "AI Assistant"
  
  ; Remove file associations
  ; DeleteRegKey HKCR ".aiassistant"
  ; DeleteRegKey HKCR "AI Assistant.File"
  
  ; Remove Start Menu shortcuts
  !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
  Delete "$SMPROGRAMS\$StartMenuFolder\AI Assistant.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall AI Assistant.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\README.lnk"
  RMDir "$SMPROGRAMS\$StartMenuFolder"
  
  ; Remove other shortcuts
  Delete "$DESKTOP\AI Assistant.lnk"
  Delete "$QUICKLAUNCH\AI Assistant.lnk"
  
  ; Remove installation directory
  RMDir /r "$INSTDIR"
  
  ; If the directory still exists, it's not empty - show message
  IfFileExists "$INSTDIR" 0 +2
    MessageBox MB_OK|MB_ICONEXCLAMATION "Note: $INSTDIR could not be completely removed because it is not empty."
SectionEnd

; -------------------------------
; CUSTOM FUNCTIONS
; -------------------------------

Function CheckWindowsVersion
  ; Check if running on Windows 10 or later
  ${If} ${AtLeastWin10}
    ; Windows 10 or later - good to go
  ${Else}
    MessageBox MB_OK|MB_ICONSTOP "AI Assistant requires Windows 10 or later.$\n$\nYour Windows version is not supported."
    Abort
  ${EndIf}
FunctionEnd

Function CheckDotNet
  ; Check for .NET Framework if needed
  ; ReadRegStr $0 HKLM "SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full" "Release"
  ; ${If} $0 < 394802  ; .NET 4.6.2
  ;   MessageBox MB_OK|MB_ICONEXCLAMATION "AI Assistant requires .NET Framework 4.6.2 or later.$\n$\nPlease install .NET Framework and run setup again."
  ;   Abort
  ; ${EndIf}
FunctionEnd
