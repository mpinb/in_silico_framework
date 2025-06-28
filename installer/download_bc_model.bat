@echo off
REM download_bc_model.bat
REM Downloads and extracts the barrel cortex model from Harvard DataVerse
REM See: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/JZPULNa

setlocal enabledelayedexpansion

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%i in ("%SCRIPT_DIR%") do set "ISF_DIR=%%~dpi"
set "ISF_DIR=%ISF_DIR:~0,-1%"
echo ISF DIR: %ISF_DIR%

REM Create barrel_cortex directory
set "BARREL_CORTEX_DIR=%ISF_DIR%\barrel_cortex"
if not exist "%BARREL_CORTEX_DIR%" mkdir "%BARREL_CORTEX_DIR%"

echo Downloading the axon tracings raw data as 7z files. These can be unzipped with 7-Zip.
echo.

REM Download 7z files using PowerShell (available on Windows 7+ with .NET)
powershell -Command "Invoke-WebRequest -Uri 'https://dataverse.harvard.edu/api/access/datafile/10256305' -OutFile '%BARREL_CORTEX_DIR%\barrel_cortex.7z.001'"
powershell -Command "Invoke-WebRequest -Uri 'https://dataverse.harvard.edu/api/access/datafile/10256306' -OutFile '%BARREL_CORTEX_DIR%\barrel_cortex.7z.002'"
powershell -Command "Invoke-WebRequest -Uri 'https://dataverse.harvard.edu/api/access/datafile/10256307' -OutFile '%BARREL_CORTEX_DIR%\barrel_cortex.7z.003'"

echo.
echo Downloading ISF-compatible barrel_cortex data:
echo.
echo     - Python code associated with the BC model (__init__.py)
echo     - average_barrel_field_L45_border.am
echo     - nrCells.csv
echo     - ConnectionsV8.csv
echo     - PST/
echo         - EXNormalizationPSTs.am
echo         - INHNormalizationsPSTs.am
echo.

REM Download individual files
powershell -Command "Invoke-WebRequest -Uri 'https://dataverse.harvard.edu/api/access/datafile/10247199' -OutFile '%BARREL_CORTEX_DIR%\__init__.py'"
powershell -Command "Invoke-WebRequest -Uri 'https://dataverse.harvard.edu/api/access/datafile/10247198' -OutFile '%BARREL_CORTEX_DIR%\average_barrel_field_L45_border.am'"
powershell -Command "Invoke-WebRequest -Uri 'https://dataverse.harvard.edu/api/access/datafile/10247202?format=original' -OutFile '%BARREL_CORTEX_DIR%\ConnectionsV8.csv'"
powershell -Command "Invoke-WebRequest -Uri 'https://dataverse.harvard.edu/api/access/datafile/10251834?format=original' -OutFile '%BARREL_CORTEX_DIR%\nrCells.csv'"
powershell -Command "Invoke-WebRequest -Uri 'https://dataverse.harvard.edu/api/access/datafile/10247203?format=original' -OutFile '%BARREL_CORTEX_DIR%\README.md'"

REM Create PST directory
if not exist "%BARREL_CORTEX_DIR%\PST" mkdir "%BARREL_CORTEX_DIR%\PST"

powershell -Command "Invoke-WebRequest -Uri 'https://dataverse.harvard.edu/api/access/datafile/10247200' -OutFile '%BARREL_CORTEX_DIR%\PST\EXNormalizationPSTs.am'"
powershell -Command "Invoke-WebRequest -Uri 'https://dataverse.harvard.edu/api/access/datafile/10247201' -OutFile '%BARREL_CORTEX_DIR%\PST\INHNormalizationsPSTs.am'"

REM Try to extract using 7-Zip
echo Extracting 7z archive...

REM Check common 7-Zip installation paths
set "SEVENZIP_EXE="
if exist "%ProgramFiles%\7-Zip\7z.exe" set "SEVENZIP_EXE=%ProgramFiles%\7-Zip\7z.exe"
if exist "%ProgramFiles(x86)%\7-Zip\7z.exe" set "SEVENZIP_EXE=%ProgramFiles(x86)%\7-Zip\7z.exe"
if exist "%ProgramW6432%\7-Zip\7z.exe" set "SEVENZIP_EXE=%ProgramW6432%\7-Zip\7z.exe"

if defined SEVENZIP_EXE (
    "%SEVENZIP_EXE%" x "%BARREL_CORTEX_DIR%\barrel_cortex.7z.001" "-o%ISF_DIR%" -y
    echo Successfully extracted barrel cortex model data
) else (
    echo WARNING: 7-Zip not found. Please:
    echo   1. Download 7-Zip from: https://www.7-zip.org/
    echo   2. Extract: %BARREL_CORTEX_DIR%\barrel_cortex.7z.001
    echo   3. To directory: %ISF_DIR%
)

echo.
echo Downloaded and extracted the barrel cortex model data to %BARREL_CORTEX_DIR%.
pause