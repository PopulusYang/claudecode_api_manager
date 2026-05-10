#Requires -Version 5.1

# ============================================
# Claude Code Settings Manager 一键安装脚本
# 自动下载源码、编译二进制、安装到环境变量
# 安装后可通过 claude-mng 命令启动
# ============================================

$ErrorActionPreference = "Stop"
$InstallerVersion = "0.0.3-beta"

# --- 颜色输出 ---
function Write-Info    { param($m) Write-Host "[INFO] $m" -ForegroundColor Green }
function Write-Warn    { param($m) Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err     { param($m) Write-Host "[ERROR] $m" -ForegroundColor Red }
function Write-Step    { param($m) Write-Host "==>$m" -ForegroundColor Cyan }

# --- 输出版本 ---
Write-Info "安装脚本版本: $InstallerVersion"

# --- 确定安装路径 ---
$BinName   = "claude-mng.exe"
$IsAdmin   = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
                 [Security.Principal.WindowsBuiltInRole]::Administrator)

if ($IsAdmin) {
    $InstallDir  = Join-Path $env:ProgramFiles "claude-mng"
    $BinDir      = Join-Path $env:ProgramFiles "claude-mng"
    $SystemInstall = $true
    Write-Info "以管理员运行,安装到系统目录 $InstallDir"
} else {
    $InstallDir  = Join-Path $env:LOCALAPPDATA "claude-mng"
    $BinDir      = Join-Path $env:LOCALAPPDATA "bin"
    $SystemInstall = $false
    Write-Warn "非管理员运行,将安装到用户目录 $InstallDir"
}

# --- 检查 Python ---
Write-Step "检查系统环境"

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    $Python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $Python) {
    Write-Err "未找到 python3,请先安装 Python 3.10+"
    Write-Err "可从 https://www.python.org/downloads/ 下载"
    exit 1
}

$PythonCmd = $Python.Source
$PyVersion = & $PythonCmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
Write-Info "Python 版本: $PyVersion"

# --- 安装构建依赖 ---
Write-Step "安装构建依赖 (PyInstaller + cryptography)"

# PyInstaller 与旧版 pathlib 不兼容, Python 3.4+ 已内置 pathlib
& $PythonCmd -m pip uninstall -y pathlib 2>$null | Out-Null

function Invoke-PipInstall {
    param([string[]]$Packages)
    # Try pip3 first, then pip, then python -m pip
    $PipCmd = $null
    if (Get-Command pip3 -ErrorAction SilentlyContinue) {
        $PipCmd = "pip3"
    } elseif (Get-Command pip -ErrorAction SilentlyContinue) {
        $PipCmd = "pip"
    } elseif (& $PythonCmd -m pip --version 2>$null) {
        $PipCmd = "$PythonCmd -m pip"
    } else {
        # Bootstrap pip
        & $PythonCmd -m ensurepip --quiet 2>$null | Out-Null
        $PipCmd = "$PythonCmd -m pip"
    }

    foreach ($pkg in $Packages) {
        Write-Host "  Installing $pkg ..." -NoNewline
        Invoke-Expression "$PipCmd install -q $pkg" 2>$null | Out-Null
        Write-Host " Done" -ForegroundColor Green
    }
}

Invoke-PipInstall -Packages @("pyinstaller", "cryptography")
Write-Info "构建依赖安装完成"

# --- 获取源码 ---
Write-Step "准备源码"

# 当通过 irm ... | iex 远程执行时, $MyInvocation.MyCommand.Definition 不可用,
# 需要先将脚本下载到临时路径,再从 GitHub 获取源码
$ScriptPath = $MyInvocation.MyCommand.Definition
if ($ScriptPath -and (Test-Path $ScriptPath -PathType Leaf)) {
    $ScriptDir = Split-Path -Parent $ScriptPath
} else {
    # 远程管道执行: 使用临时目录
    $ScriptDir = Join-Path $env:TEMP "claude-mng-install-$PID"
    if (-not (Test-Path $ScriptDir)) {
        New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null
    }
}
$SourceFile = Join-Path $ScriptDir "claude_settings_manager.py"

if (Test-Path $SourceFile) {
    Write-Info "检测到本地源码,使用当前目录"
    $BuildDir = $ScriptDir
    $CopySource = $true
} else {
    Write-Info "未检测到本地源码,尝试从 GitHub 下载"

    # 优先尝试直接下载单个 Python 文件 (不需要 git)
    $RepoBranch = "main"
    $RawBaseUrl = "https://raw.githubusercontent.com/PopulusYang/claudecode_api_manager/$RepoBranch"
    $SourceUrl = "$RawBaseUrl/claude_settings_manager.py"

    try {
        Write-Info "下载 $SourceUrl ..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $SourceUrl -OutFile $SourceFile -UseBasicParsing

        # 同时下载卸载脚本
        $UninstallUrl = "$RawBaseUrl/uninstall.ps1"
        $UninstallDest = Join-Path $ScriptDir "uninstall.ps1"
        try {
            Write-Info "下载卸载脚本 ..."
            Invoke-WebRequest -Uri $UninstallUrl -OutFile $UninstallDest -UseBasicParsing
        } catch {
            Write-Warn "下载卸载脚本失败: $($_.Exception.Message)"
        }

        $BuildDir = $ScriptDir
        $CopySource = $true
        Write-Info "源码下载完成"
    } catch {
        Write-Warn "直接下载失败,尝试使用 git 克隆"

        if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
            Write-Err "未找到 git,也无法下载源码,请手动安装"
            exit 1
        }

        $RepoUrl = Read-Host "请输入仓库地址 (直接回车使用默认)"
        if ([string]::IsNullOrWhiteSpace($RepoUrl)) {
            $RepoUrl = "https://github.com/PopulusYang/claudecode_api_manager.git"
        }

        if (-not (Test-Path $InstallDir)) {
            New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
        }
        & git clone $RepoUrl $InstallDir
        $BuildDir = $InstallDir
        $CopySource = $false
    }
}

# --- 编译二进制 ---
Write-Step "编译为二进制文件"

$BuildTemp = Join-Path $BuildDir "build_temp"
if (Test-Path $BuildTemp) { Remove-Item -Recurse -Force $BuildTemp }

$DistPath  = Join-Path $BuildTemp "dist"
$WorkPath  = Join-Path $BuildTemp "work"
$SpecPath  = Join-Path $BuildTemp "spec"
$SourcePy  = Join-Path $BuildDir "claude_settings_manager.py"

& pyinstaller `
    --onefile `
    --name claude-mng `
    --distpath $DistPath `
    --workpath $WorkPath `
    --specpath $SpecPath `
    --hidden-import cryptography `
    --hidden-import cryptography.fernet `
    --hidden-import cryptography.hazmat.primitives.hashes `
    --hidden-import cryptography.hazmat.primitives.kdf.pbkdf2 `
    --log-level WARN `
    $SourcePy 2>&1 | Where-Object { $_ -notmatch "^\d+\s+INFO" }

if ($LASTEXITCODE -ne 0) {
    Write-Err "PyInstaller 编译失败"
    exit 1
}

Write-Info "编译完成"

# --- 安装到 PATH ---
Write-Step "安装到 $BinDir"

if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
}

$BuiltExe  = Join-Path $DistPath "claude-mng.exe"
$TargetExe = Join-Path $BinDir $BinName

if (Test-Path $TargetExe) {
    $Overwrite = Read-Host "$TargetExe 已存在,是否覆盖? [y/N]"
    if ($Overwrite -notmatch '^[Yy]') {
        Write-Info "取消安装"
        exit 0
    }
}

Copy-Item -Path $BuiltExe -Destination $TargetExe -Force
Write-Info "已安装到 $TargetExe"

# --- 安装卸载脚本 ---
$UninstallSource = Join-Path $ScriptDir "uninstall.ps1"
$UninstallTarget = Join-Path $BinDir "uninstall.ps1"
if (Test-Path $UninstallSource) {
    Copy-Item -Path $UninstallSource -Destination $UninstallTarget -Force
    Write-Info "已安装卸载脚本到 $UninstallTarget"
} else {
    Write-Warn "未找到 uninstall.ps1,无法安装卸载脚本"
}

# --- 确保 BinDir 在 PATH 中 ---
$UserPath  = [Environment]::GetEnvironmentVariable("PATH", "User")
$SystemPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")

$InPath = ($env:PATH -split [IO.Path]::PathSeparator) -contains $BinDir

if (-not $InPath) {
    $CurrentUserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    $NewPath = "$BinDir;$CurrentUserPath"
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    $env:PATH = "$BinDir;$env:PATH"
    Write-Info "已将 $BinDir 加入用户 PATH(当前会话已生效)"
}

# --- 清理构建产物 ---
if (Test-Path $BuildTemp) { Remove-Item -Recurse -Force $BuildTemp }

# --- 检查 Claude Code CLI ---
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Warn "未检测到 Claude Code CLI"
    $InstallClaude = Read-Host "是否现在安装 Claude Code CLI? (需要 npm) [y/N]"
    if ($InstallClaude -match '^[Yy]') {
        if (Get-Command npm -ErrorAction SilentlyContinue) {
            Write-Step "安装 Claude Code CLI"
            & npm install -g @anthropic-ai/claude-code
        } else {
            Write-Warn "未找到 npm,请手动安装: npm install -g @anthropic-ai/claude-code"
        }
    } else {
        Write-Info "已跳过"
    }
} else {
    Write-Info "Claude Code CLI 已就绪"
}

# --- 交互式配置 ---
Write-Host ""
Write-Host "============================================"
Write-Host "  Claude Code 国内AI厂商配置"
Write-Host "============================================"
Write-Host ""
Write-Host "请选择要配置的提供商:"
Write-Host "  1) DeepSeek"
Write-Host "  2) 阿里云百炼"
Write-Host "  3) 智谱 GLM"
Write-Host "  4) 跳过配置,稍后手动运行"
Write-Host ""

$Choice = Read-Host "请选择 [1-4]"

switch ($Choice) {
    "1" {
        $ApiKey = Read-Host "请输入 DeepSeek API Key (sk-...)"
        Write-Host "请选择模型:"
        Write-Host "  1) deepseek-chat"
        Write-Host "  2) deepseek-reasoner"
        Write-Host "  3) deepseek-v4-flash"
        Write-Host "  4) deepseek-v4-pro"
        $ModelChoice = Read-Host "请选择 [1-4]"
        switch ($ModelChoice) {
            "1" { $Model = "deepseek-chat" }
            "2" { $Model = "deepseek-reasoner" }
            "3" { $Model = "deepseek-v4-flash[1m]" }
            "4" { $Model = "deepseek-v4-pro[1m]" }
            default { $Model = "deepseek-chat" }
        }
        & claude-mng config deepseek $ApiKey $Model --scope global
    }
    "2" {
        $ApiKey = Read-Host "请输入阿里云 API Key (sk-...)"
        $AliyunModel = Read-Host "请选择模型 (默认 qwen3.6-plus)"
        if ([string]::IsNullOrWhiteSpace($AliyunModel)) {
            $AliyunModel = "qwen3.6-plus"
        }
        Write-Host "请选择计费方案:"
        Write-Host "  1) Coding Plan"
        Write-Host "  2) 按量计费 (payg)"
        Write-Host "  3) Token Plan 团队版"
        $PlanChoice = Read-Host "请选择 [1-3]"
        switch ($PlanChoice) {
            "1" { $Plan = "coding" }
            "2" { $Plan = "payg" }
            "3" { $Plan = "token_team" }
            default { $Plan = "coding" }
        }
        & claude-mng config aliyun $ApiKey $AliyunModel --plan $Plan --scope global
    }
    "3" {
        $ApiKey = Read-Host "请输入智谱 API Key"
        Write-Host "请选择模型:"
        Write-Host "  1) GLM-4.7"
        Write-Host "  2) GLM-4.5-Air"
        Write-Host "  3) GLM-5.1"
        Write-Host "  4) GLM-5-Turbo"
        $ModelChoice = Read-Host "请选择 [1-4]"
        switch ($ModelChoice) {
            "1" { $Model = "GLM-4.7" }
            "2" { $Model = "GLM-4.5-Air" }
            "3" { $Model = "GLM-5.1" }
            "4" { $Model = "GLM-5-Turbo" }
            default { $Model = "GLM-4.7" }
        }
        & claude-mng config zhipu $ApiKey $Model --scope global
    }
    default {
        Write-Info "跳过配置,稍后运行: claude-mng"
    }
}

Write-Host ""
Write-Host "============================================"
Write-Host "  安装完成!"
Write-Host "============================================"
Write-Host ""
Write-Host "使用方式:"
Write-Host "  claude-mng                   # 启动交互式配置"
Write-Host "  claude-mng list              # 列出所有提供商"
Write-Host "  claude-mng show              # 查看当前配置"
Write-Host "  claude-mng price             # 查看价格参考"
Write-Host "  claude-mng uninstall         # 卸载本程序"
Write-Host "  claude                       # 启动 Claude Code"
Write-Host ""
