#!/usr/bin/env bash
set -euo pipefail

# ============================================
# Claude Code Settings Manager 一键卸载脚本
# 删除二进制、安装目录和 PATH 环境变量
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

log_info "卸载脚本版本: ${INSTALLER_VERSION}"

BIN_NAME="claude-mng"

# --- 解析参数 ---
CALLER_BIN_DIR=""
CALLER_INSTALL_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bin-dir) CALLER_BIN_DIR="$2"; shift 2 ;;
        --install-dir) CALLER_INSTALL_DIR="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [[ -n "$CALLER_BIN_DIR" && -n "$CALLER_INSTALL_DIR" ]]; then
    log_info "使用调用者传入的安装路径"
    log_info "安装目录: ${CALLER_INSTALL_DIR}"
    log_info "二进制目录: ${CALLER_BIN_DIR}"
    BIN_PATH="${CALLER_BIN_DIR}/${BIN_NAME}"
    INSTALL_DIR="${CALLER_INSTALL_DIR}"
    SYSTEM_INSTALL=false
else
    # 无参数时根据权限推断路径
    BIN_PATH="/usr/local/bin/${BIN_NAME}"
    INSTALL_DIR="/opt/claude-mng"
    if [[ $EUID -eq 0 ]]; then
        log_info "以 root 运行，将卸载系统目录 ${INSTALL_DIR}"
        SYSTEM_INSTALL=true
    else
        INSTALL_DIR="${HOME}/.local/claude-mng"
        BIN_PATH="${HOME}/.local/bin/${BIN_NAME}"
        SYSTEM_INSTALL=false
        log_info "将卸载用户目录安装 ${INSTALL_DIR}"
    fi
fi

log_step "检查安装状态"

FOUND=false

if [[ -f "${BIN_PATH}" ]]; then
    log_info "找到已安装的二进制: ${BIN_PATH}"
    FOUND=true
fi
if [[ -d "${INSTALL_DIR}" ]]; then
    log_info "找到安装目录: ${INSTALL_DIR}"
    FOUND=true
fi

if [[ "$FOUND" == false ]]; then
    log_warn "未检测到 Claude Code Settings Manager 的安装"
    exit 0
fi

# --- 确认卸载 ---
echo ""
read -rp "确认卸载? 这将删除上述文件 [y/N]: " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    log_info "取消卸载"
    exit 0
fi

# --- 删除二进制 ---
log_step "删除二进制文件"

if [[ -f "${BIN_PATH}" ]]; then
    rm -f "${BIN_PATH}"
    log_info "已删除 ${BIN_PATH}"
fi

# --- 删除安装目录 ---
log_step "删除安装目录"

if [[ -d "${INSTALL_DIR}" ]]; then
    rm -rf "${INSTALL_DIR}"
    log_info "已删除 ${INSTALL_DIR}"
fi

# --- 清理 PATH (非 root 安装) ---
if [[ "$SYSTEM_INSTALL" == false ]]; then
    log_step "清理 PATH 环境变量"

    LOCAL_BIN="$(dirname "${BIN_PATH}")"
    if [[ ":$PATH:" == *":${LOCAL_BIN}:"* ]]; then
        # 从当前会话 PATH 中移除
        PATH=$(echo "$PATH" | tr ':' '\n' | grep -v "^${LOCAL_BIN}$" | paste -sd ':' -)
        export PATH
    fi

    # 从 shell 配置中移除相关行
    for rcfile in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.bash_profile" "${HOME}/.profile"; do
        if [[ -f "$rcfile" ]] && grep -q ".local/bin.*claude-mng\|claude-mng.*.local/bin" "$rcfile" 2>/dev/null; then
            sed -i '/\.local\/bin.*claude-mng\|claude-mng.*\.local\/bin/d' "$rcfile"
            log_info "已从 $rcfile 中移除 PATH 条目"
        fi
    done
fi

echo ""
echo "============================================"
echo "  卸载完成!"
echo "============================================"
echo ""
echo "如需重新安装，运行:"
echo "  curl -fsSL https://raw.githubusercontent.com/PopulusYang/claudecode_api_manager/main/install.sh | bash"
echo ""
