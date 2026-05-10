__app_version__ = "0.0.3-beta"

"""
Claude Code Settings Manager - 国内AI厂商配置管理器
支持 DeepSeek、阿里云百炼、智谱GLM 等国内厂商的按量付费配置
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    print("  缺少 cryptography 库，请先安装:")
    print("  pip install cryptography")
    sys.exit(1)

try:
    import getpass

    HAS_GETPASS = True
except ImportError:
    HAS_GETPASS = False


PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "website": "https://platform.deepseek.com",
        "base_url": "https://api.deepseek.com/anthropic",
        "env_key": "ANTHROPIC_AUTH_TOKEN",
        "env_extra": {
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
        "models": [
            {
                "id": "deepseek-chat",
                "display": "DeepSeek Chat (deepseek-chat)",
                "note": "通用对话模型，2026-07-24 后迁移到 deepseek-v4-flash",
                "price_input_hit": 0.5,
                "price_input_miss": 2.0,
                "price_output": 8.0,
            },
            {
                "id": "deepseek-reasoner",
                "display": "DeepSeek Reasoner (deepseek-reasoner)",
                "note": "推理模型，2026-07-24 后迁移到 deepseek-v4-pro",
                "price_input_hit": 1.0,
                "price_input_miss": 4.0,
                "price_output": 16.0,
            },
            {
                "id": "deepseek-v4-flash[1m]",
                "display": "DeepSeek V4 Flash [1m] (新版)",
                "note": "新版轻量模型，支持 1M 上下文",
                "price_input_hit": 0.14,
                "price_input_miss": 0.99,
                "price_output": 5.90,
            },
            {
                "id": "deepseek-v4-pro[1m]",
                "display": "DeepSeek V4 Pro [1m] (新版)",
                "note": "新版旗舰模型，支持 1M 上下文，限时2.5折至 2026-05-31",
                "price_input_hit": 0.28,
                "price_input_miss": 2.20,
                "price_output": 11.00,
            },
        ],
        "default_model": "deepseek-chat",
        "model_mapping": {
            "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-chat",
            "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-chat",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-chat",
        },
    },
    "aliyun": {
        "name": "阿里云百炼（通义千问）",
        "website": "https://bailian.console.aliyun.com",
        "env_key": "ANTHROPIC_AUTH_TOKEN",
        "plans": {
            "token_team": {
                "name": "Token Plan 团队版",
                "base_url": "https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic",
                "note": "按坐席订阅，按 token 消耗抵扣 Credits",
                "model_mapping": {
                    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3.6-plus",
                    "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3.6-plus",
                    "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen3.6-plus",
                    "CLAUDE_CODE_SUBAGENT_MODEL": "qwen3.6-plus",
                },
            },
            "coding": {
                "name": "Coding Plan",
                "base_url": "https://coding.dashscope.aliyuncs.com/apps/anthropic",
                "note": "固定月费，轻量版 ¥40/月，专业版 ¥200/月",
                "model_mapping": {
                    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3.6-flash",
                    "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3.6-plus",
                    "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen3.6-plus",
                    "CLAUDE_CODE_SUBAGENT_MODEL": "qwen3.6-plus",
                },
            },
            "payg": {
                "name": "按量计费 (Pay-as-you-go)",
                "base_url": "https://dashscope.aliyuncs.com/apps/anthropic",
                "note": "按实际调用量后付费，新加坡节点: dashscope-intl.aliyuncs.com",
                "model_mapping": {
                    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3.6-flash",
                    "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3.6-plus",
                    "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen3.6-plus",
                    "CLAUDE_CODE_SUBAGENT_MODEL": "qwen3.6-plus",
                },
            },
        },
        "models": [
            {
                "id": "qwen3.6-plus",
                "display": "Qwen3.6-Plus",
                "note": "最新旗舰模型",
                "price_input_hit": None,
                "price_input_miss": None,
                "price_output": None,
            },
            {
                "id": "qwen3.6-flash",
                "display": "Qwen3.6-Flash",
                "note": "最新轻量快速模型",
                "price_input_hit": None,
                "price_input_miss": None,
                "price_output": None,
            },
            {
                "id": "qwen3-coder-plus",
                "display": "Qwen3-Coder-Plus",
                "note": "最强编程模型，输入 ¥7.34 / 输出 ¥36.70 每百万Tokens",
                "price_input_hit": 7.34,
                "price_input_miss": 7.34,
                "price_output": 36.70,
            },
            {
                "id": "qwen3-coder-turbo",
                "display": "Qwen3-Coder-Turbo",
                "note": "高性价比编程模型",
                "price_input_hit": 3.50,
                "price_input_miss": 3.50,
                "price_output": 17.50,
            },
            {
                "id": "qwen3-max",
                "display": "Qwen3-Max",
                "note": "通用旗舰模型",
                "price_input_hit": 2.80,
                "price_input_miss": 2.80,
                "price_output": 11.20,
            },
            {
                "id": "qwen3-plus",
                "display": "Qwen3-Plus",
                "note": "均衡模型",
                "price_input_hit": 0.40,
                "price_input_miss": 0.40,
                "price_output": 1.20,
            },
        ],
        "default_model": "qwen3.6-plus",
    },
    "zhipu": {
        "name": "智谱 GLM",
        "website": "https://open.bigmodel.cn",
        "base_url": "https://open.bigmodel.cn/api/anthropic",
        "env_key": "ANTHROPIC_AUTH_TOKEN",
        "env_extra": {
            "API_TIMEOUT_MS": "3000000",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
        },
        "models": [
            {
                "id": "GLM-4.7",
                "display": "GLM-4.7",
                "note": "当前默认模型，对应 Claude Opus/Sonnet",
                "price_input_hit": None,
                "price_input_miss": None,
                "price_output": None,
            },
            {
                "id": "GLM-4.5-Air",
                "display": "GLM-4.5-Air",
                "note": "轻量模型，对应 Claude Haiku",
                "price_input_hit": None,
                "price_input_miss": None,
                "price_output": None,
            },
            {
                "id": "GLM-5.1",
                "display": "GLM-5.1",
                "note": "2026年4月旗舰，低峰期 1x 抵扣",
                "price_input_hit": None,
                "price_input_miss": None,
                "price_output": None,
            },
            {
                "id": "GLM-5-Turbo",
                "display": "GLM-5-Turbo",
                "note": "高阶模型，对标 Claude Opus，低峰期 1x 抵扣至 6月底",
                "price_input_hit": None,
                "price_input_miss": None,
                "price_output": None,
            },
            {
                "id": "GLM-5",
                "display": "GLM-5",
                "note": "高阶模型，对标 Claude Opus",
                "price_input_hit": None,
                "price_input_miss": None,
                "price_output": None,
            },
        ],
        "default_model": "GLM-4.7",
        "model_mapping": {
            "ANTHROPIC_DEFAULT_OPUS_MODEL": "GLM-4.7",
            "ANTHROPIC_DEFAULT_SONNET_MODEL": "GLM-4.7",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "GLM-4.5-Air",
        },
    },
}


# 所有可能被提供商设置的 env key 集合
ALL_PROVIDER_ENV_KEYS = {
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "API_TIMEOUT_MS",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
}


def collect_all_provider_env_keys() -> set:
    keys = set(ALL_PROVIDER_ENV_KEYS)
    for pv in PROVIDERS.values():
        keys.update(pv.get("env_extra", {}).keys())
        keys.update(pv.get("model_mapping", {}).keys())
        if "plans" in pv:
            for pl in pv["plans"].values():
                keys.update(pl.get("model_mapping", {}).keys())
    return keys


def _clean_stale_env(env: dict, provider_key: str):
    """移除不属于当前提供商的残留 env key"""
    all_keys = collect_all_provider_env_keys()
    provider = PROVIDERS[provider_key]
    current_keys = {"ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"}
    current_keys.update(provider.get("env_extra", {}).keys())
    current_keys.update(provider.get("model_mapping", {}).keys())
    if "plans" in provider:
        for pl in provider["plans"].values():
            current_keys.update(pl.get("model_mapping", {}).keys())

    for k in all_keys:
        if k not in current_keys and k in env:
            del env[k]


BACKUP_DIR = Path.cwd() / "claudebackup"


def backup_settings(path: Path):
    """备份原配置文件到 claudebackup 目录，文件名附加时间戳"""
    if not path.exists():
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{path.stem}_{timestamp}{path.suffix}"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(path, backup_path)
    print(f"  已备份: {backup_path}")


VAULT_PATH = Path.home() / ".claude" / "api_keys.json"


class APIVault:
    """加密 API Key 存储，使用 Fernet + PBKDF2"""

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        return kdf.derive(password.encode("utf-8"))

    @staticmethod
    def _encrypt(plaintext: str, password: str) -> str:
        import base64

        salt = os.urandom(16)
        key = APIVault._derive_key(password, salt)
        fernet = Fernet(base64.urlsafe_b64encode(key))
        encrypted = fernet.encrypt(plaintext.encode("utf-8"))
        return json.dumps(
            {
                "salt": base64.urlsafe_b64encode(salt).decode(),
                "data": encrypted.decode(),
            }
        )

    @staticmethod
    def _decrypt(cipher_json: str, password: str) -> str:
        import base64

        obj = json.loads(cipher_json)
        salt = base64.urlsafe_b64decode(obj["salt"])
        key = APIVault._derive_key(password, salt)
        fernet = Fernet(base64.urlsafe_b64encode(key))
        return fernet.decrypt(obj["data"].encode()).decode("utf-8")

    @staticmethod
    def load_vault() -> dict:
        if VAULT_PATH.exists():
            with open(VAULT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"keys": {}}

    @staticmethod
    def save_vault(vault: dict):
        VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(VAULT_PATH, "w", encoding="utf-8") as f:
            json.dump(vault, f, indent=2, ensure_ascii=False)

    @staticmethod
    def add_key(label: str, api_key: str, password: str):
        vault = APIVault.load_vault()
        vault["keys"][label] = APIVault._encrypt(api_key, password)
        APIVault.save_vault(vault)

    @staticmethod
    def get_key(label: str, password: str) -> str:
        vault = APIVault.load_vault()
        if label not in vault["keys"]:
            raise KeyError(f"找不到标签: {label}")
        return APIVault._decrypt(vault["keys"][label], password)

    @staticmethod
    def list_labels() -> list:
        vault = APIVault.load_vault()
        return list(vault["keys"].keys())

    @staticmethod
    def remove_key(label: str):
        vault = APIVault.load_vault()
        if label in vault["keys"]:
            del vault["keys"][label]
            APIVault.save_vault(vault)
            return True
        return False


def ask_password(prompt: str = "请输入主密码") -> str:
    """安全读取主密码，fallback 到普通 input"""
    if HAS_GETPASS:
        return getpass.getpass(f"{prompt}: ")
    return input(f"{prompt} (明文可见): ").strip()


def get_settings_path(scope="project"):
    """获取 settings.json 路径"""
    if scope == "global":
        return Path.home() / ".claude" / "settings.json"
    else:
        return Path.cwd() / ".claude" / "settings.json"


def load_settings(path):
    """加载 settings.json"""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_settings(path, settings, do_backup=True):
    """保存 settings.json，默认先备份再写入"""
    if do_backup:
        backup_settings(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    print(f"  已保存: {path}")


def confirm_global():
    """全局配置操作前确认"""
    print("\n  ⚠️  警告: 即将修改全局 Claude Code 配置 (~/.claude/settings.json)")
    print("  这将影响所有项目的 Claude Code 行为。")
    confirm = input("  确认继续? (y/N): ").strip().lower()
    if confirm != "y" and confirm != "yes":
        print("  已取消")
        return False
    return True


def build_env_config(provider_key, api_key, model=None, plan=None):
    """构建环境变量配置"""
    provider = PROVIDERS[provider_key]
    env = {}

    if "plans" in provider:
        # 阿里云：从 plan 中获取 base_url 和 model_mapping
        plan_choice = plan or "payg"
        plan_info = provider["plans"][plan_choice]
        env["ANTHROPIC_BASE_URL"] = plan_info["base_url"]
        if plan_info.get("model_mapping"):
            for k, v in plan_info["model_mapping"].items():
                env[k] = v
    else:
        # DeepSeek / 智谱
        env["ANTHROPIC_BASE_URL"] = provider["base_url"]
        if provider.get("model_mapping"):
            for k, v in provider["model_mapping"].items():
                env[k] = v

    # 统一使用 ANTHROPIC_AUTH_TOKEN
    env["ANTHROPIC_AUTH_TOKEN"] = api_key

    # 提供商额外环境变量
    for k, v in provider.get("env_extra", {}).items():
        env[k] = v

    # 用户指定模型
    if model:
        env["ANTHROPIC_MODEL"] = model

    return env


def apply_config(
    scope, provider_key, api_key, model=None, plan=None, merge=True, do_backup=True
):
    """应用配置到 settings.json"""
    # 全局配置前确认
    if scope == "global" and not confirm_global():
        return

    settings_path = get_settings_path(scope)
    settings = load_settings(settings_path) if merge else {}

    if "env" not in settings:
        settings["env"] = {}

    # 清除之前提供商的残留 key
    _clean_stale_env(settings["env"], provider_key)

    env = build_env_config(provider_key, api_key, model, plan)

    for k, v in env.items():
        settings["env"][k] = v

    save_settings(settings_path, settings, do_backup=do_backup)

    provider = PROVIDERS[provider_key]
    provider_name = provider["name"]
    model_id = model or provider.get("default_model", "unknown")
    print(f"\n  配置已应用: {provider_name} / {model_id}")
    print(f"  作用域: {scope} ({settings_path})")


def show_current_config(scope="project"):
    """显示当前配置"""
    settings_path = get_settings_path(scope)
    if not settings_path.exists():
        print(f"  未找到配置文件: {settings_path}")
        return

    settings = load_settings(settings_path)
    env = settings.get("env", {})

    if not env:
        print("  当前配置中没有环境变量")
        return

    print(f"\n  当前配置 ({settings_path}):")
    print("  " + "=" * 50)

    base_url = env.get("ANTHROPIC_BASE_URL", "未设置")
    api_key = env.get("ANTHROPIC_AUTH_TOKEN", env.get("ANTHROPIC_API_KEY", "未设置"))
    model = env.get("ANTHROPIC_MODEL", "默认")

    key_display = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 15 else api_key

    matched_provider = None
    for pk, pv in PROVIDERS.items():
        if pv.get("base_url") == base_url:
            matched_provider = pv
            break
        if "plans" in pv:
            for pl in pv["plans"].values():
                if pl["base_url"] == base_url:
                    matched_provider = pv
                    break

    provider_name = matched_provider["name"] if matched_provider else "未知来源"

    print(f"  提供商:    {provider_name}")
    print(f"  Base URL: {base_url}")
    print(f"  API Key:  {key_display}")
    print(f"  模型:     {model}")
    print("  " + "=" * 50)


def show_pricing(provider_key=None):
    """显示价格信息"""
    providers_to_show = [provider_key] if provider_key else PROVIDERS.keys()

    for pk in providers_to_show:
        if pk not in PROVIDERS:
            print(f"  未知提供商: {pk}")
            continue

        provider = PROVIDERS[pk]
        print(f"\n  {'=' * 60}")
        print(f"  {provider['name']}")
        print(f"  官网: {provider['website']}")
        print(f"  {'=' * 60}")
        print(f"  {'模型':<28} {'输入(命中)':<12} {'输入(未命中)':<12} {'输出':<12}")
        print(f"  {'-' * 28} {'-' * 12} {'-' * 12} {'-' * 12}")

        for m in provider["models"]:
            hit = (
                f"¥{m['price_input_hit']}" if m["price_input_hit"] is not None else "-"
            )
            miss = (
                f"¥{m['price_input_miss']}"
                if m["price_input_miss"] is not None
                else "-"
            )
            out = f"¥{m['price_output']}" if m["price_output"] is not None else "-"
            print(f"  {m['display']:<28} {hit:<12} {miss:<12} {out:<12}")

        if "plans" in provider:
            print(f"\n  计费方案:")
            for plan_k, plan_v in provider["plans"].items():
                print(f"    - {plan_v['name']}: {plan_v['note']}")
        print()


def show_providers():
    """列出所有支持的提供商"""
    print(f"\n  {'=' * 50}")
    print(f"  支持的 AI 提供商")
    print(f"  {'=' * 50}")

    for pk, pv in PROVIDERS.items():
        print(f"\n  [{pk}] {pv['name']}")
        print(f"      官网: {pv['website']}")
        if "plans" in pv:
            for plan_k, plan_v in pv["plans"].items():
                print(f"      方案: {plan_v['name']}")
        else:
            print(f"      Base URL: {pv['base_url']}")
        print(f"      默认模型: {pv.get('default_model', 'N/A')}")

    print()


def _select_api_key() -> str:
    """让用户选择已保存的 API Key 或输入新的。返回 API Key 字符串。"""
    labels = APIVault.list_labels()

    if labels:
        print(f"\n已保存的 API Key:")
        for i, label in enumerate(labels, 1):
            print(f"  {i}. {label}")
        print(f"  {len(labels) + 1}. 输入新的 API Key")

        choice = input(f"\n请选择 (1-{len(labels) + 1}, 回车=输入新的): ").strip()
        if choice:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(labels):
                    # 选择已有 key，需要密码解密
                    password = ask_password("请输入主密码")
                    try:
                        return APIVault.get_key(labels[idx], password)
                    except Exception:
                        print("  密码错误，无法解密。请重新输入 API Key。")
                        return input("\n输入 API Key: ").strip()
                elif idx == len(labels):
                    pass  # fall through to new input
                else:
                    print("  无效选择，请输入新的 API Key。")
            except ValueError:
                print("  无效输入，请输入新的 API Key。")

    api_key = input("\n输入 API Key: ").strip()
    if not api_key:
        print("  API Key 不能为空")
        return ""

    # 询问是否保存
    save_choice = input("\n是否保存此 API Key? (y/N): ").strip().lower()
    if save_choice in ("y", "yes"):
        label = input("  为此 API Key 取一个标签 (例如: deepseek-main): ").strip()
        if not label:
            label = f"key-{len(labels) + 1}"
        password = ask_password("请设置主密码（用于加密保存）")
        confirm = ask_password("请再次输入主密码")
        if password != confirm:
            print("  两次密码不一致，未保存。")
        else:
            try:
                APIVault.add_key(label, api_key, password)
                print(f"  已保存 API Key: {label}")
            except Exception as e:
                print(f"  保存失败: {e}")

    return api_key


def interactive_config():
    """交互式配置向导"""
    print("\n" + "=" * 50)
    print("  Claude Code Settings Manager")
    print("  国内AI厂商配置管理器")
    print("=" * 50)

    print("\n选择提供商:")
    provider_keys = list(PROVIDERS.keys())
    for i, pk in enumerate(provider_keys, 1):
        pv = PROVIDERS[pk]
        print(f"  {i}. {pk} - {pv['name']}")

    choice = input(f"\n请选择 (1-{len(provider_keys)}): ").strip()
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(provider_keys):
            print("  无效选择")
            return
        provider_key = provider_keys[idx]
    except ValueError:
        print("  无效输入")
        return

    provider = PROVIDERS[provider_key]
    print(f"\n已选择: {provider['name']}")

    if "plans" in provider:
        print(f"\n选择计费方案:")
        plan_keys = list(provider["plans"].keys())
        for i, pk in enumerate(plan_keys, 1):
            pv = provider["plans"][pk]
            print(f"  {i}. {pv['name']} - {pv['note']}")

        plan_choice = input(f"\n请选择 (1-{len(plan_keys)}): ").strip()
        try:
            plan_idx = int(plan_choice) - 1
            plan_key = plan_keys[plan_idx]
        except (ValueError, IndexError):
            print("  无效选择，使用默认方案")
            plan_key = plan_keys[0]
    else:
        plan_key = None

    print(f"\n可用模型:")
    for i, m in enumerate(provider["models"], 1):
        print(f"  {i}. {m['display']}")
        print(f"     {m['note']}")

    model_choice = input(
        f"\n选择模型 (1-{len(provider['models'])}, 回车使用默认): "
    ).strip()
    if model_choice:
        try:
            model_idx = int(model_choice) - 1
            model = provider["models"][model_idx]["id"]
        except (ValueError, IndexError):
            print(f"  无效选择，使用默认模型: {provider.get('default_model')}")
            model = provider.get("default_model")
    else:
        model = provider.get("default_model")

    api_key = _select_api_key()
    if not api_key:
        return

    print(f"\n作用域:")
    print(f"  1. project - 当前项目 (.claude/settings.json)")
    print(f"  2. global  - 全局 (~/.claude/settings.json)")

    scope_choice = input("\n请选择 (1-2, 回车=project): ").strip()
    scope = "global" if scope_choice == "2" else "project"

    apply_config(scope, provider_key, api_key, model, plan_key)

    print(f"\n  下一步: 在终端运行 'claude' 启动")


# --------------- Vault Management Commands ---------------


def vault_list():
    """列出所有已保存的 API Key 标签"""
    labels = APIVault.list_labels()
    if not labels:
        print("  未保存任何 API Key")
        return
    print("\n  已保存的 API Key 标签:")
    for label in labels:
        print(f"    - {label}")


def vault_add(label=None, api_key=None, password=None):
    """添加 API Key 到加密存储"""
    if not label:
        label = input("标签名称 (例如: deepseek-main): ").strip()
    if not api_key:
        api_key = input("API Key: ").strip()
    if not password:
        password = ask_password("设置主密码")
        confirm = ask_password("确认主密码")
        if password != confirm:
            print("  两次密码不一致")
            return

    if not label or not api_key:
        print("  标签和 API Key 不能为空")
        return

    APIVault.add_key(label, api_key, password)
    print(f"  已保存: {label}")


def vault_get(label):
    """解密并显示指定 API Key"""
    password = ask_password("请输入主密码")
    try:
        key = APIVault.get_key(label, password)
        print(f"\n  {label}: {key}")
    except KeyError:
        print(f"  找不到: {label}")
    except Exception:
        print("  密码错误或解密失败")


def vault_remove(label):
    """从加密存储中删除 API Key"""
    if APIVault.remove_key(label):
        print(f"  已删除: {label}")
    else:
        print(f"  未找到: {label}")


def remove_config(scope, provider_key=None, do_backup=True):
    """移除配置"""
    # 全局配置操作前确认
    if scope == "global" and not confirm_global():
        return

    settings_path = get_settings_path(scope)
    if not settings_path.exists():
        print(f"  未找到配置文件: {settings_path}")
        return

    settings = load_settings(settings_path)
    env = settings.get("env", {})

    if not env:
        print("  当前配置为空")
        return

    if provider_key and provider_key in PROVIDERS:
        provider = PROVIDERS[provider_key]

        # 收集所有需要清理的 env key
        keys_to_remove = set()

        # 1. API Key
        keys_to_remove.add("ANTHROPIC_AUTH_TOKEN")

        # 2. 提供商额外环境变量
        if provider.get("env_extra"):
            keys_to_remove.update(provider["env_extra"].keys())

        # 3. 提供商或 plan 的 model_mapping
        if provider.get("model_mapping"):
            keys_to_remove.update(provider["model_mapping"].keys())
        if "plans" in provider:
            for pl in provider["plans"].values():
                if pl.get("model_mapping"):
                    keys_to_remove.update(pl["model_mapping"].keys())

        # 4. 如果 ANTHROPIC_BASE_URL 匹配此提供商，一并移除
        current_base_url = env.get("ANTHROPIC_BASE_URL")
        if current_base_url:
            if provider.get("base_url") and current_base_url == provider["base_url"]:
                keys_to_remove.add("ANTHROPIC_BASE_URL")
            if "plans" in provider:
                for pl in provider["plans"].values():
                    if current_base_url == pl["base_url"]:
                        keys_to_remove.add("ANTHROPIC_BASE_URL")
                        break

        # 5. 如果 ANTHROPIC_MODEL 指向此提供商的某个模型，一并移除
        current_model = env.get("ANTHROPIC_MODEL")
        if current_model:
            model_ids = {m["id"] for m in provider["models"]}
            if current_model in model_ids:
                keys_to_remove.add("ANTHROPIC_MODEL")

        removed = []
        for k in keys_to_remove:
            if k in env:
                del env[k]
                removed.append(k)

        if removed:
            settings["env"] = env
            save_settings(settings_path, settings, do_backup=do_backup)
            print(f"  已移除 {provider['name']} 配置: {', '.join(removed)}")
        else:
            print(f"  未找到 {provider_key} 相关的配置")
    else:
        settings["env"] = {}
        save_settings(settings_path, settings, do_backup=do_backup)
        print("  已清除所有环境变量配置")


def do_uninstall(no_backup: bool = False, no_cache: bool = False):
    """交互式卸载:备份配置/缓存后删除程序"""

    exe_path = os.path.abspath(
        sys.executable if getattr(sys, "frozen", False) else __file__
    )
    bin_dir = os.path.dirname(exe_path)
    is_frozen = getattr(sys, "frozen", False)

    # 查找卸载脚本
    if sys.platform == "win32":
        uninstall_script = os.path.join(bin_dir, "uninstall.ps1")
    else:
        uninstall_script = os.path.join(bin_dir, "uninstall.sh")

    # 检查安装目录
    install_dir = bin_dir
    if sys.platform == "win32" and bin_dir.lower().endswith("bin"):
        parent = os.path.dirname(bin_dir)
        alt_dir = os.path.join(parent, "claude-mng")
        if os.path.isdir(alt_dir):
            install_dir = alt_dir
        elif os.path.isdir(r"C:\Program Files\claude-mng"):
            install_dir = r"C:\Program Files\claude-mng"
    elif sys.platform != "win32":
        if os.path.isdir("/opt/claude-mng"):
            install_dir = "/opt/claude-mng"
        elif os.path.isdir(os.path.expanduser("~/.local/claude-mng")):
            install_dir = os.path.expanduser("~/.local/claude-mng")

    # 收集需要清理的内容
    clauderc = Path.home() / ".claude" / "CLAUDE.json"
    clauderc_global = Path.home() / ".claude" / "CLAUDE.global.json"
    cache_dir = Path.home() / ".claude" / "cache"

    has_settings = clauderc.exists() or clauderc_global.exists()
    has_cache = cache_dir.exists() and any(cache_dir.iterdir())
    has_uninstall_script = os.path.isfile(uninstall_script)

    print()
    print("============================================")
    print("  Claude Code Settings Manager 卸载")
    print("============================================")
    print()
    print("即将卸载以下内容:")

    if has_settings:
        print("  [ ] Claude Code 配置文件 (CLAUDE.json)")
    if has_cache:
        print("  [ ] API 缓存数据")
    print(f"  [ ] 二进制程序 (位于 {bin_dir})")
    if os.path.isdir(install_dir) and install_dir != bin_dir:
        print(f"  [ ] 安装目录 ({install_dir})")
    print()

    # 备份配置文件
    if not no_backup and has_settings:
        ans = input("是否备份配置文件到 ~/.claude/backup/ ? [Y/n]: ").strip()
        if ans.lower() not in ("n", "no"):
            backup_dir = Path.home() / ".claude" / "backup"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            for f in (clauderc, clauderc_global):
                if f.exists():
                    dst = backup_dir / f"{f.name}.{ts}.bak"
                    shutil.copy2(f, dst)
                    print(f"  已备份 {f} -> {dst}")

    # 清除 API 缓存
    if not no_cache and has_cache:
        ans = input("是否清除 API 缓存? [y/N]: ").strip()
        if ans.lower() in ("y", "yes"):
            shutil.rmtree(cache_dir)
            print("  已清除 API 缓存")

    # 删除原始配置文件
    if not no_backup and has_settings:
        ans = input("是否保留原始配置文件? [Y/n]: ").strip()
        if ans.lower() in ("n", "no"):
            if clauderc.exists():
                clauderc.unlink()
                print("  已删除 CLAUDE.json")
            if clauderc_global.exists():
                clauderc_global.unlink()
                print("  已删除 CLAUDE.global.json")

    # 确认卸载
    print()
    confirm = input("确认继续卸载? 这将删除本程序 [y/N]: ").strip()
    if confirm.lower() not in ("y", "yes"):
        print("  已取消卸载")
        return

    # 运行卸载脚本
    if has_uninstall_script:
        print()
        print("  运行卸载脚本...")
        if sys.platform == "win32":
            # Windows: 生成临时 bat, 等待本进程退出后再执行卸载脚本
            bat = os.path.join(os.environ.get("TEMP", ""), "claude-mng-uninstall.bat")
            with open(bat, "w") as f:
                f.write(f"@echo off\n")
                f.write(f"timeout /t 2 /nobreak >nul\n")
                f.write(
                    f'powershell -ExecutionPolicy Bypass -File "{uninstall_script}" '
                    f'-BinDir "{bin_dir}" -InstallDir "{install_dir}"\n'
                )
                f.write(f'del "%~f0"\n')
            subprocess.Popen(["cmd", "/c", "start", "/min", bat], shell=True)
        else:
            os.chmod(uninstall_script, 0o755)
            os.system(
                f'bash "{uninstall_script}" --bin-dir "{bin_dir}" --install-dir "{install_dir}"'
            )
    else:
        # 没有卸载脚本时,使用延迟自删
        print()
        print("  未找到卸载脚本，使用延迟自删...")
        if sys.platform == "win32":
            bat = os.path.join(os.environ.get("TEMP", ""), "claude-mng-uninstall.bat")
            self_exe = exe_path
            if not self_exe.endswith(".exe"):
                self_exe = os.path.join(bin_dir, "claude-mng.exe")
            with open(bat, "w") as f:
                f.write(f"@echo off\n")
                f.write(f"timeout /t 2 /nobreak >nul\n")
                f.write(f'del /f /q "{self_exe}"\n')
                if os.path.isdir(install_dir):
                    f.write(f'rmdir /s /q "{install_dir}"\n')
                f.write(f'del "%~f0"\n')
            subprocess.Popen(["cmd", "/c", "start", "/min", bat], shell=True)
        else:
            if os.path.isfile(exe_path):
                os.remove(exe_path)
            if os.path.isdir(install_dir):
                shutil.rmtree(install_dir, ignore_errors=True)

    print()


def build_parser():
    """构建 argparse 参数解析器"""
    parser = argparse.ArgumentParser(
        prog="claude-mng",
        description="Claude Code Settings Manager - 国内AI厂商配置管理器",
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"%(prog)s {__app_version__}"
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("list", help="列出所有支持的提供商")

    price_p = sub.add_parser("price", help="显示价格信息")
    price_p.add_argument("provider", nargs="?", default=None, help="提供商名称")

    config_p = sub.add_parser("config", help="配置提供商")
    config_p.add_argument("provider", choices=list(PROVIDERS.keys()), help="提供商")
    config_p.add_argument("api_key", help="API Key")
    config_p.add_argument("model", nargs="?", default=None, help="模型名称（可选）")
    config_p.add_argument(
        "--scope",
        choices=["project", "global"],
        default="project",
        help="作用域: project（当前项目）或 global（全局，默认 project）",
    )
    config_p.add_argument(
        "--plan", default=None, help="计费方案（仅阿里云: token_team / coding / payg）"
    )
    config_p.add_argument(
        "--no-backup", "-nbk", action="store_true", help="不备份原配置文件"
    )

    show_p = sub.add_parser("show", help="显示当前配置")
    show_p.add_argument(
        "--scope",
        choices=["project", "global"],
        default="project",
        help="作用域（默认 project）",
    )

    remove_p = sub.add_parser("remove", help="移除配置")
    remove_p.add_argument(
        "provider", nargs="?", default=None, help="提供商名称（可选，留空则清除所有）"
    )
    remove_p.add_argument(
        "--scope",
        choices=["project", "global"],
        default="project",
        help="作用域（默认 project）",
    )
    remove_p.add_argument(
        "--no-backup", "-nbk", action="store_true", help="不备份原配置文件"
    )

    clear_p = sub.add_parser("clear", help="清除所有环境变量配置")
    clear_p.add_argument(
        "--scope",
        choices=["project", "global"],
        default="project",
        help="作用域（默认 project）",
    )
    clear_p.add_argument(
        "--no-backup", "-nbk", action="store_true", help="不备份原配置文件"
    )

    sub.add_parser("interactive", help="交互式配置向导")
    sub.add_parser("help", help="显示帮助信息")

    uninstall_p = sub.add_parser("uninstall", help="卸载本程序及相关配置")
    uninstall_p.add_argument(
        "--no-backup", action="store_true", default=False, help="不备份配置文件"
    )
    uninstall_p.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="不清除 API 缓存（默认保留）",
    )

    # Vault commands
    vault_p = sub.add_parser("vault", help="管理加密的 API Key 存储")
    vault_sub = vault_p.add_subparsers(dest="vault_cmd", metavar="<action>")

    vault_sub.add_parser("list", help="列出已保存的 API Key 标签")

    va_p = vault_sub.add_parser("add", help="添加 API Key")
    va_p.add_argument("label", nargs="?", default=None, help="标签名")
    va_p.add_argument("api_key", nargs="?", default=None, help="API Key")

    vg_p = vault_sub.add_parser("get", help="查看 API Key (解密)")
    vg_p.add_argument("label", help="标签名")

    vr_p = vault_sub.add_parser("delete", help="删除 API Key")
    vr_p.add_argument("label", help="标签名")

    return parser


def main():
    parser = build_parser()

    # 无参数时显示帮助
    if len(sys.argv) < 2:
        parser.print_help()
        return

    args = parser.parse_args()

    if args.command == "list":
        show_providers()

    elif args.command == "price":
        show_pricing(args.provider)

    elif args.command == "config":
        do_backup = not args.no_backup
        apply_config(
            args.scope,
            args.provider,
            args.api_key,
            args.model,
            args.plan,
            do_backup=do_backup,
        )

    elif args.command == "show":
        show_current_config(args.scope)

    elif args.command == "remove":
        remove_config(args.scope, args.provider, do_backup=not args.no_backup)

    elif args.command == "clear":
        remove_config(args.scope, do_backup=not args.no_backup)

    elif args.command == "interactive":
        interactive_config()

    elif args.command == "help":
        parser.print_help()

    elif args.command == "uninstall":
        do_uninstall(no_backup=args.no_backup, no_cache=args.no_cache)

    elif args.command == "vault":
        if args.vault_cmd == "list":
            vault_list()
        elif args.vault_cmd == "add":
            vault_add(args.label, args.api_key)
        elif args.vault_cmd == "get":
            vault_get(args.label)
        elif args.vault_cmd == "delete":
            vault_remove(args.label)
        else:
            print("  用法: claude_settings_manager vault <list|add|get|delete>")
            print("  运行 claude_settings_manager vault --help 查看详细信息")


if __name__ == "__main__":
    main()
