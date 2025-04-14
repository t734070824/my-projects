@echo off
chcp 65001 >nul  


powershell -Command "(New-Object Net.WebClient).DownloadFile('https://www.sumatrapdfreader.org/dl/rel/3.5.2/SumatraPDF-3.5.2-64-install.exe', 'D:\github\my-projects\SumatraPDF.exe')"
if %errorlevel% neq 0 (
    echo 下载失败，建议以管理员身份运行脚本[9](@ref)
) else (
    echo 下载成功  SumatraPDF.exe
)



pause