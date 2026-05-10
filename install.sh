#!/usr/bin/env bash
set -euo pipefail

# ============================================
# Claude Code Settings Manager 一键安装脚本
# 自动下载源码、编译二进制、安装到环境变量
# 安装后可通过 claude-mng 命令启动
# ============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALLER_VERSION="0.0.4-beta"

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${CYAN}==> $1${NC}"; }

log_info "安装脚本版本: ${INSTALLER_VERSION}"

INSTALL_DIR="/opt/claude-mng"
BIN_NAME="claude-mng"
BIN_PATH="/usr/local/bin/${BIN_NAME}"

# --- 权限检测 ---
log_step "检查系统环境"

if [[ $EUID -eq 0 ]]; then
    log_info "以 root 运行，安装到系统目录 ${INSTALL_DIR}"
    SYSTEM_INSTALL=true
else
    log_warn "非 root 运行，将安装到用户目录 ~/.local/claude-mng"
    INSTALL_DIR="${HOME}/.local/claude-mng"
    BIN_PATH="${HOME}/.local/bin/${BIN_NAME}"
    SYSTEM_INSTALL=false
    mkdir -p "${HOME}/.local/bin"
fi

if ! command -v python3 &>/dev/null; then
    log_error "未找到 python3，请先安装 Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log_info "Python 版本: ${PYTHON_VERSION}"

# --- 安装构建依赖 ---
log_step "安装构建依赖 (PyInstaller + cryptography)"

if command -v pip3 &>/dev/null; then
    pip3 install -q pyinstaller cryptography
elif command -v pip &>/dev/null; then
    pip install -q pyinstaller cryptography
else
    python3 -m ensurepip --quiet 2>/dev/null || true
    python3 -m pip install -q pyinstaller cryptography
fi

log_info "构建依赖安装完成"

# --- 获取源码 ---
log_step "准备源码"

# 兼容 curl | bash 管道模式: BASH_SOURCE 可能为空
if [[ -n "${BASH_SOURCE[0]+x}" && -f "${BASH_SOURCE[0]}" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    SCRIPT_DIR="$(pwd)"
fi

if [[ -f "${SCRIPT_DIR}/claude_settings_manager.py" ]]; then
    log_info "检测到本地源码，使用当前目录"
    BUILD_DIR="${SCRIPT_DIR}"
    COPY_SOURCE=true
else
    log_info "未检测到本地源码，尝试从 GitHub 下载"

    REPO_BRANCH="main"
    RAW_BASE_URL="https://raw.githubusercontent.com/PopulusYang/claudecode_api_manager/${REPO_BRANCH}"
    SOURCE_URL="${RAW_BASE_URL}/claude_settings_manager.py"

    mkdir -p "${SCRIPT_DIR}"

    if curl -fsSL "${SOURCE_URL}" -o "${SCRIPT_DIR}/claude_settings_manager.py" 2>/dev/null; then
        # 同时下载卸载脚本
        UNINSTALL_URL="${RAW_BASE_URL}/uninstall.sh"
        curl -fsSL "${UNINSTALL_URL}" -o "${SCRIPT_DIR}/uninstall.sh" 2>/dev/null || true

        BUILD_DIR="${SCRIPT_DIR}"
        COPY_SOURCE=true
        log_info "源码下载完成"
    else
        log_warn "直接下载失败，将从 GitHub 克隆"
        read -rp "请输入仓库地址 (直接回车使用默认): " repo_url
        repo_url="${repo_url:-https://github.com/PopulusYang/claudecode_api_manager.git}"
        git clone "$repo_url" "${INSTALL_DIR}"
        BUILD_DIR="${INSTALL_DIR}"
        COPY_SOURCE=false
    fi
fi

# --- 编译二进制 ---
log_step "编译为二进制文件"

BUILD_TEMP="${BUILD_DIR}/build_temp"
rm -rf "${BUILD_TEMP}"

pyinstaller \
    --onefile \
    --name claude-mng \
    --distpath "${BUILD_TEMP}/dist" \
    --workpath "${BUILD_TEMP}/work" \
    --specpath "${BUILD_TEMP}/spec" \
    --hidden-import cryptography \
    --hidden-import cryptography.fernet \
    --hidden-import cryptography.hazmat.primitives.hashes \
    --hidden-import cryptography.hazmat.primitives.kdf.pbkdf2 \
    "${BUILD_DIR}/claude_settings_manager.py" \
    --log-level WARN

log_info "编译完成"

# --- 安装到 PATH ---
log_step "安装到 ${BIN_PATH}"

if [[ -f "${BIN_PATH}" ]]; then
    # 非交互模式(管道执行)自动覆盖，交互模式询问
    if [[ -t 0 ]]; then
        read -rp "${BIN_PATH} 已存在，是否覆盖? [y/N]: " overwrite
        if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
            log_info "取消安装"
            exit 0
        fi
    fi
fi

if $SYSTEM_INSTALL; then
    mkdir -p /usr/local/bin
else
    mkdir -p "${HOME}/.local/bin"
fi
cp "${BUILD_TEMP}/dist/claude-mng" "${BIN_PATH}"
chmod +x "${BIN_PATH}"

# --- 安装卸载脚本 ---
UNINSTALL_SRC="${SCRIPT_DIR}/uninstall.sh"
UNINSTALL_DST="${HOME}/.local/claude-mng/uninstall.sh"
if $SYSTEM_INSTALL; then
    UNINSTALL_DST="/opt/claude-mng/uninstall.sh"
fi
mkdir -p "$(dirname "${UNINSTALL_DST}")"
if [[ -f "${UNINSTALL_SRC}" ]]; then
    cp "${UNINSTALL_SRC}" "${UNINSTALL_DST}"
    chmod +x "${UNINSTALL_DST}"
    log_info "已安装卸载脚本到 ${UNINSTALL_DST}"
else
    log_warn "未找到 uninstall.sh，无法安装卸载脚本"
fi

if ! $SYSTEM_INSTALL; then
    echo ""
    log_info "请将 ${HOME}/.local/bin 加入 PATH:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo "" >> "${HOME}/.bashrc"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "${HOME}/.bashrc"
        log_info "已自动写入 ~/.bashrc"
    fi
fi

# --- 清理构建产物 ---
rm -rf "${BUILD_TEMP}"

# --- 检查 Claude Code CLI ---
if ! command -v claude &>/dev/null; then
    echo ""
    log_warn "未检测到 Claude Code CLI"
    read -rp "是否现在安装 Claude Code CLI? (需要 npm) [y/N]: " install_claude
    if [[ "$install_claude" =~ ^[Yy]$ ]]; then
        if command -v npm &>/dev/null; then
            log_step "安装 Claude Code CLI"
            npm install -g @anthropic-ai/claude-code
        else
            log_warn "未找到 npm，请手动安装: npm install -g @anthropic-ai/claude-code"
        fi
    else
        log_info "已跳过"
    fi
else
    log_info "Claude Code CLI 已就绪"
fi

# --- 交互式配置 ---
echo ""
echo "============================================"
echo "  Claude Code 国内AI厂商配置"
echo "============================================"
echo ""
echo "请选择要配置的提供商："
echo "  1) DeepSeek"
echo "  2) 阿里云百炼"
echo "  3) 智谱 GLM"
echo "  4) 跳过配置，稍后手动运行"
echo ""
read -rp "请选择 [1-4]: " choice

case "$choice" in
    1)
        read -rp "请输入 DeepSeek API Key (sk-...): " api_key
        read -rp "请选择模型 [1=deepseek-chat, 2=deepseek-reasoner, 3=deepseek-v4-flash, 4=deepseek-v4-pro]: " model_choice
        case "$model_choice" in
            1) model="deepseek-chat" ;;
            2) model="deepseek-reasoner" ;;
            3) model="deepseek-v4-flash[1m]" ;;
            4) model="deepseek-v4-pro[1m]" ;;
            *) model="deepseek-chat" ;;
        esac
        claude-mng config deepseek "$api_key" "$model" --scope global
        ;;
    2)
        read -rp "请输入阿里云 API Key (sk-...): " api_key
        read -rp "请选择模型 (默认 qwen3.6-plus): " aliyun_model
        aliyun_model="${aliyun_model:-qwen3.6-plus}"
        echo "请选择计费方案："
        echo "  1) Coding Plan"
        echo "  2) 按量计费 (payg)"
        echo "  3) Token Plan 团队版"
        read -rp "请选择 [1-3]: " plan_choice
        case "$plan_choice" in
            1) plan="coding" ;;
            2) plan="payg" ;;
            3) plan="token_team" ;;
            *) plan="coding" ;;
        esac
        claude-mng config aliyun "$api_key" "$aliyun_model" --plan "$plan" --scope global
        ;;
    3)
        read -rp "请输入智谱 API Key: " api_key
        read -rp "请选择模型 [1=GLM-4.7, 2=GLM-4.5-Air, 3=GLM-5.1, 4=GLM-5-Turbo]: " model_choice
        case "$model_choice" in
            1) model="GLM-4.7" ;;
            2) model="GLM-4.5-Air" ;;
            3) model="GLM-5.1" ;;
            4) model="GLM-5-Turbo" ;;
            *) model="GLM-4.7" ;;
        esac
        claude-mng config zhipu "$api_key" "$model" --scope global
        ;;
    *)
        log_info "跳过配置，稍后运行: claude-mng"
        ;;
esac

echo ""
echo "============================================"
echo "  安装完成！"
echo "============================================"
echo ""
echo "使用方式："
echo "  claude-mng                   # 启动交互式配置"
echo "  claude-mng list              # 列出所有提供商"
echo "  claude-mng show              # 查看当前配置"
echo "  claude-mng price             # 查看价格参考"
echo "  claude-mng uninstall         # 卸载本程序"
echo "  claude                       # 启动 Claude Code"
echo ""
