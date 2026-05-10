# Claude Code Settings Manager

满足一些人（包括我）不翻墙使用Claude code的需求
国内 AI 厂商 Claude Code 配置管理器，支持 DeepSeek、阿里云百炼、智谱 GLM。


 ## 一键安装

**Linux / macOS:**

 ```bash
 curl -sSL https://raw.githubusercontent.com/PopulusYang/claudecode_api_manager/main/install.sh | bash
 ```

**Windows (PowerShell):**

 ```powershell
 irm https://raw.githubusercontent.com/PopulusYang/claudecode_api_manager/main/install.ps1 | iex
 ```

## 支持的提供商

| 提供商 | 官网 | 计费方案 |
|--------|------|----------|
| DeepSeek | <https://platform.deepseek.com> | 按量付费 |
| 阿里云百炼 | <https://bailian.console.aliyun.com> | Token Plan 团队版 / Coding Plan / 按量计费 |
| 智谱 GLM | <https://open.bigmodel.cn> | Coding Plan |

## 价格参考

### DeepSeek（每百万 Tokens，人民币）

| 模型 | 输入(缓存命中) | 输入(缓存未命中) | 输出 |
|------|---------------|-----------------|------|
| deepseek-chat | ¥0.5 | ¥2.0 | ¥8.0 |
| deepseek-reasoner | ¥1.0 | ¥4.0 | ¥16.0 |
| deepseek-v4-flash[1m] | ¥0.14 | ¥0.99 | ¥5.90 |
| deepseek-v4-pro[1m] | ¥0.28 | ¥2.20 | ¥11.00 |

### 阿里云百炼（每百万 Tokens，人民币）

| 模型 | 输入 | 输出 |
|------|------|------|
| qwen3.6-plus | - | - |
| qwen3.6-flash | - | - |
| qwen3-coder-plus | ¥7.34 | ¥36.70 |
| qwen3-coder-turbo | ¥3.50 | ¥17.50 |
| qwen3-max | ¥2.80 | ¥11.20 |
| qwen3-plus | ¥0.40 | ¥1.20 |

### 智谱 GLM

| 模型 | 说明 |
|------|------|
| GLM-4.7 | 当前默认，对应 Claude Opus/Sonnet |
| GLM-4.5-Air | 轻量模型，对应 Claude Haiku |
| GLM-5.1 | 2026年4月旗舰，低峰期 1x 抵扣 |
| GLM-5-Turbo | 高阶模型，低峰期 1x 抵扣至 6月底 |

## 安装

```bash
git clone <repo>
cd claudecode_api_manager
```

## 使用

### 交互式配置（推荐）

```bash
python claude_settings_manager.py
```

### 命令行配置

```bash
# 列出所有提供商
python claude_settings_manager.py list

# 查看价格
python claude_settings_manager.py price
python claude_settings_manager.py price deepseek

# 配置 DeepSeek
python claude_settings_manager.py config deepseek sk-xxx deepseek-chat

# 配置阿里云 Coding Plan
python claude_settings_manager.py config aliyun sk-xxx qwen3.6-plus --plan coding

# 配置阿里云按量计费
python claude_settings_manager.py config aliyun sk-xxx qwen3.6-plus --plan payg

# 配置阿里云 Token Plan 团队版
python claude_settings_manager.py config aliyun sk-xxx qwen3.6-plus --plan token_team

# 配置智谱
python claude_settings_manager.py config zhipu your_api_key GLM-4.7

# 全局配置（写入 ~/.claude/settings.json，会提示确认）
python claude_settings_manager.py config deepseek sk-xxx --scope global

# 查看当前配置
python claude_settings_manager.py show

# 移除配置
python claude_settings_manager.py remove deepseek

# 清除所有配置
python claude_settings_manager.py clear
```

## 配置原理

工具会将配置写入 `.claude/settings.json` 的 `env` 字段。所有提供商统一使用 `ANTHROPIC_AUTH_TOKEN` 传递 API Key：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_MODEL": "deepseek-chat",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-chat",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-chat",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-chat"
  }
}
```

Claude Code 启动时会读取此文件中的环境变量，实现第三方模型接入。

## 手动配置参考

### DeepSeek

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-chat",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-chat",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-chat",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```

### 阿里云百炼

三种方案使用不同的 Base URL，统一使用 `ANTHROPIC_AUTH_TOKEN`：

#### Token Plan 团队版

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_BASE_URL": "https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic",
    "ANTHROPIC_MODEL": "qwen3.6-plus",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3.6-plus",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3.6-plus",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen3.6-plus",
    "CLAUDE_CODE_SUBAGENT_MODEL": "qwen3.6-plus"
  }
}
```

#### Coding Plan

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_BASE_URL": "https://coding.dashscope.aliyuncs.com/apps/anthropic",
    "ANTHROPIC_MODEL": "qwen3.6-plus",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3.6-flash",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3.6-plus",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen3.6-plus",
    "CLAUDE_CODE_SUBAGENT_MODEL": "qwen3.6-plus"
  }
}
```

#### 按量计费

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_BASE_URL": "https://dashscope.aliyuncs.com/apps/anthropic",
    "ANTHROPIC_MODEL": "qwen3.6-plus",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3.6-flash",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3.6-plus",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen3.6-plus",
    "CLAUDE_CODE_SUBAGENT_MODEL": "qwen3.6-plus"
  }
}
```

新加坡节点：`https://dashscope-intl.aliyuncs.com/apps/anthropic`

### 智谱 GLM

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "your_zhipu_api_key",
    "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1
  }
}
```

默认模型映射：

- `ANTHROPIC_DEFAULT_OPUS_MODEL` → `GLM-4.7`
- `ANTHROPIC_DEFAULT_SONNET_MODEL` → `GLM-4.7`
- `ANTHROPIC_DEFAULT_HAIKU_MODEL` → `GLM-4.5-Air`

## 开源许可

本项目当前使用的开源程序如下：

| 程序 | 用途 | 许可 |
|------|------|------|
| cryptography | 加密、密钥派生与 Fernet 支持 | Apache-2.0 OR BSD-3-Clause |
| cffi | cryptography 的运行时依赖 | MIT |
| pycparser | cffi 的运行时依赖 | BSD-3-Clause |

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
