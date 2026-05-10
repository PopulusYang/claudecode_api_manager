#Requires -Version 5.1

# ============================================
# Claude Code Settings Manager 一键卸载脚本
# 删除二进制、安装目录和 PATH 环境变量
# ============================================

param(
    [string]$BinDir = "",
    [string]$InstallDir = ""
)

$ErrorActionPreference = "Stop"
$InstallerVersion = "0.0.4-beta"

# --- 颜色输出 ---
function Write-Info    { param($m) Write-Host "[INFO] $m" -ForegroundColor Green }
function Write-Warn    { param($m) Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err     { param($m) Write-Host "[ERROR] $m" -ForegroundColor Red }
function Write-Step    { param($m) Write-Host "==>$m" -ForegroundColor Cyan }

$BinName = "claude-mng.exe"

Write-Info "卸载脚本版本: $InstallerVersion"

if ($BinDir -and $InstallDir) {
    Write-Info "使用调用者传入的安装路径"
    Write-Info "安装目录: $InstallDir"
    Write-Info "二进制目录: $BinDir"
} else {
    # 无参数时根据权限推断路径
    $IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
                   [Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($IsAdmin) {
        $InstallDir  = Join-Path $env:ProgramFiles "claude-mng"
        $BinDir      = Join-Path $env:ProgramFiles "claude-mng"
        Write-Info "以管理员运行,将卸载系统目录 $InstallDir"
    } else {
        $InstallDir  = Join-Path $env:LOCALAPPDATA "claude-mng"
        $BinDir      = Join-Path $env:LOCALAPPDATA "bin"
        Write-Info "将卸载用户目录安装 $InstallDir"
    }
}

Write-Step "检查安装状态"

$TargetExe = Join-Path $BinDir $BinName
$Found = $false

if (Test-Path $TargetExe) {
    Write-Info "找到已安装的二进制: $TargetExe"
    $Found = $true
}
if (Test-Path $InstallDir) {
    Write-Info "找到安装目录: $InstallDir"
    $Found = $true
}

if (-not $Found) {
    Write-Warn "未检测到 Claude Code Settings Manager 的安装"
    exit 0
}

# --- 确认卸载 ---
Write-Host ""
$Confirm = Read-Host "确认卸载? 这将删除上述文件 [y/N]"
if ($Confirm -notmatch '^[Yy]') {
    Write-Info "取消卸载"
    exit 0
}

# --- 删除二进制 ---
Write-Step "删除二进制文件"

if (Test-Path $TargetExe) {
    Remove-Item -Path $TargetExe -Force
    Write-Info "已删除 $TargetExe"
}

# --- 删除安装目录 ---
Write-Step "删除安装目录"

if (Test-Path $InstallDir) {
    Remove-Item -Path $InstallDir -Recurse -Force
    Write-Info "已删除 $InstallDir"
}

# --- 从 PATH 中移除 ---
Write-Step "清理 PATH 环境变量"

$UserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$InPath = ($UserPath -split [IO.Path]::PathSeparator) -contains $BinDir

if ($InPath) {
    $NewPath = (($UserPath -split [IO.Path]::PathSeparator) | Where-Object { $_ -ne $BinDir }) -join [IO.Path]::PathSeparator
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    Write-Info "已从用户 PATH 中移除 $BinDir"
} else {
    Write-Info "$BinDir 不在 PATH 中,无需清理"
}

# --- 从当前会话 PATH 中移除 ---
$env:PATH = (($env:PATH -split [IO.Path]::PathSeparator) | Where-Object { $_ -ne $BinDir }) -join [IO.Path]::PathSeparator

# --- 清理构建产物(如果源码仍在本地) ---
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if ($SourceDir -and (Test-Path "$SourceDir\build_temp")) {
    Remove-Item -Path "$SourceDir\build_temp" -Recurse -Force
    Write-Info "已清理本地构建产物"
}

Write-Host ""
Write-Host "============================================"
Write-Host "  卸载完成!"
Write-Host "============================================"
Write-Host ""
Write-Host "如需重新安装,运行:"
Write-Host "  irm https://raw.githubusercontent.com/PopulusYang/claudecode_api_manager/main/install.ps1 | iex"
Write-Host ""
