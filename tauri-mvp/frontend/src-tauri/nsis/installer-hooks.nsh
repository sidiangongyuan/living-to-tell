!include LogicLib.nsh

!ifdef __NSD_CheckBox_STYLE
  !undef __NSD_CheckBox_STYLE
!endif
!define __NSD_CheckBox_STYLE ${WS_CHILD}|${WS_CLIPSIBLINGS}|${WS_TABSTOP}|${BS_TEXT}|${BS_VCENTER}|${BS_AUTOCHECKBOX}|${BS_MULTILINE}

!macro WRITER_PROCESS_EXISTS PROCESS_NAME RESULT_VAR
  nsExec::ExecToStack 'cmd /C tasklist /FI "IMAGENAME eq ${PROCESS_NAME}" /NH 2>NUL | find /I "${PROCESS_NAME}" >NUL'
  Pop $R9
  Pop $R8
  StrCpy ${RESULT_VAR} "0"
  ${If} $R9 == 0
    StrCpy ${RESULT_VAR} "1"
  ${EndIf}
!macroend

!macro WRITER_KILL_PROCESS PROCESS_NAME
  nsExec::ExecToStack 'cmd /C taskkill /F /T /IM "${PROCESS_NAME}" 2>NUL'
  Pop $R9
  Pop $R8
!macroend

!macro WRITER_DELETE_INSTALL_FILE FILE_NAME
  ${If} ${FileExists} "$INSTDIR\${FILE_NAME}"
    ClearErrors
    Delete "$INSTDIR\${FILE_NAME}"
    ${If} ${Errors}
      MessageBox MB_ICONSTOP|MB_OK "The installer could not replace $INSTDIR\${FILE_NAME}.$\r$\n$\r$\nPlease close 活着为了讲述 / Living to Tell from Task Manager and run the installer again.$\r$\n$\r$\nYour writing data will not be deleted."
      Abort "Could not replace ${FILE_NAME}."
    ${EndIf}
    ${If} ${FileExists} "$INSTDIR\${FILE_NAME}"
      MessageBox MB_ICONSTOP|MB_OK "The installer could not remove $INSTDIR\${FILE_NAME}.$\r$\n$\r$\nInstallation was stopped to avoid a partial update.$\r$\n$\r$\nYour writing data will not be deleted."
      Abort "Could not remove ${FILE_NAME}."
    ${EndIf}
  ${EndIf}
!macroend

!macro WRITER_CHECK_AND_CLOSE_RUNNING_APP
  StrCpy $R0 "0"
  !insertmacro WRITER_PROCESS_EXISTS "living-to-tell-app.exe" $R1
  ${If} $R1 == "1"
    StrCpy $R0 "1"
  ${EndIf}
  !insertmacro WRITER_PROCESS_EXISTS "活着为了讲述.exe" $R1
  ${If} $R1 == "1"
    StrCpy $R0 "1"
  ${EndIf}
  !insertmacro WRITER_PROCESS_EXISTS "living-to-tell-backend.exe" $R1
  ${If} $R1 == "1"
    StrCpy $R0 "1"
  ${EndIf}
  !insertmacro WRITER_PROCESS_EXISTS "writer-app.exe" $R1
  ${If} $R1 == "1"
    StrCpy $R0 "1"
  ${EndIf}
  !insertmacro WRITER_PROCESS_EXISTS "Writer.exe" $R1
  ${If} $R1 == "1"
    StrCpy $R0 "1"
  ${EndIf}
  !insertmacro WRITER_PROCESS_EXISTS "writer-backend.exe" $R1
  ${If} $R1 == "1"
    StrCpy $R0 "1"
  ${EndIf}

  ${If} $R0 == "1"
    MessageBox MB_ICONEXCLAMATION|MB_OKCANCEL "活着为了讲述 / Living to Tell is still running.$\r$\n$\r$\nPlease make sure your writing is saved. The installer will close the app and its background service before continuing." IDOK close_writer IDCANCEL cancel_install
    cancel_install:
      Abort "Living to Tell is still running. Installation was cancelled."
    close_writer:
      !insertmacro WRITER_KILL_PROCESS "living-to-tell-app.exe"
      !insertmacro WRITER_KILL_PROCESS "活着为了讲述.exe"
      !insertmacro WRITER_KILL_PROCESS "living-to-tell-backend.exe"
      !insertmacro WRITER_KILL_PROCESS "writer-app.exe"
      !insertmacro WRITER_KILL_PROCESS "Writer.exe"
      !insertmacro WRITER_KILL_PROCESS "writer-backend.exe"
      Sleep 1200

      StrCpy $R0 "0"
      !insertmacro WRITER_PROCESS_EXISTS "living-to-tell-app.exe" $R1
      ${If} $R1 == "1"
        StrCpy $R0 "1"
      ${EndIf}
      !insertmacro WRITER_PROCESS_EXISTS "活着为了讲述.exe" $R1
      ${If} $R1 == "1"
        StrCpy $R0 "1"
      ${EndIf}
      !insertmacro WRITER_PROCESS_EXISTS "living-to-tell-backend.exe" $R1
      ${If} $R1 == "1"
        StrCpy $R0 "1"
      ${EndIf}
      !insertmacro WRITER_PROCESS_EXISTS "writer-app.exe" $R1
      ${If} $R1 == "1"
        StrCpy $R0 "1"
      ${EndIf}
      !insertmacro WRITER_PROCESS_EXISTS "Writer.exe" $R1
      ${If} $R1 == "1"
        StrCpy $R0 "1"
      ${EndIf}
      !insertmacro WRITER_PROCESS_EXISTS "writer-backend.exe" $R1
      ${If} $R1 == "1"
        StrCpy $R0 "1"
      ${EndIf}

      ${If} $R0 == "1"
        MessageBox MB_ICONSTOP|MB_OK "活着为了讲述 / Living to Tell could not be closed automatically.$\r$\n$\r$\nPlease close it from Task Manager and run the installer again."
        Abort "Living to Tell is still running."
      ${EndIf}
  ${EndIf}
!macroend

!macro NSIS_HOOK_PREINSTALL
  !insertmacro WRITER_CHECK_AND_CLOSE_RUNNING_APP
  !insertmacro WRITER_DELETE_INSTALL_FILE "living-to-tell-backend.exe"
  !insertmacro WRITER_DELETE_INSTALL_FILE "writer-backend.exe"
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  StrCpy $DeleteAppDataCheckboxState 0
  !insertmacro WRITER_CHECK_AND_CLOSE_RUNNING_APP
!macroend
