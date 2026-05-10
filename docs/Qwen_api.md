Claude Code 是 Anthropic 推出的命令行 AI 编程助手，可以通过按量计费、Coding Plan 或 Token Plan 团队版接入阿里云百炼。

## **安装 Claude Code**

### 安装

## macOS

1. 安装或更新 [Node.js](https://nodejs.org/en/download/)（v18.0 或更高版本）。

2. 在终端中执行下列命令，安装 Claude Code。

    ```
    npm install -g @anthropic-ai/claude-code
    ```

3. 运行以下命令验证安装。若有版本号输出，则表示安装成功。

    ```
    claude --version
    ```

## Windows

在 Windows 上使用 Claude Code，需要安装 WSL 或 [Git for Windows](https://git-scm.com/install/windows)，然后在 WSL 或 Git Bash 中执行以下命令。

```
npm install -g @anthropic-ai/claude-code
```

> 详情可以参考Claude Code官方文档的[Windows安装教程](https://docs.anthropic.com/en/docs/claude-code/setup#windows-setup)。

### 跳过登录验证

编辑或新增 `~/.claude.json`（Windows 路径：`C:\Users\<用户名>\.claude.json`），将 `hasCompletedOnboarding` 设置为 `true`，跳过 Anthropic 官方登录验证。

```
{
  "hasCompletedOnboarding": true
}
```

## **配置接入凭证**

创建 `~/.claude/settings.json`（Windows 路径：`C:\Users\<用户名>\.claude\settings.json`），根据所选方案写入对应配置。阿里云百炼提供三种计费方案，根据需要选择：

- **Token Plan 团队版**：按坐席订阅，按 token 消耗抵扣 Credits。

- **Coding Plan**：固定月费订阅，按模型调用次数计量。

- **按量计费**：按实际调用量后付费。

### Token Plan 团队版

将 YOUR\_API\_KEY 替换为 Token Plan 团队版专属 [API Key](https://bailian.console.aliyun.com/?tab=plan#/efm/subscription/overview)。可用模型请参考 Token Plan 团队版[支持的模型](https://help.aliyun.com/zh/model-studio/token-plan-overview)。

```
{
    "env": {
        "ANTHROPIC_AUTH_TOKEN": "YOUR_API_KEY",
        "ANTHROPIC_BASE_URL": "https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic",
        "ANTHROPIC_MODEL": "qwen3.6-plus",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3.6-plus",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3.6-plus",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen3.6-plus",
        "CLAUDE_CODE_SUBAGENT_MODEL": "qwen3.6-plus"
    }
}
```

### Coding Plan

将 YOUR\_API\_KEY 替换为 Coding Plan 专属 [API Key](https://bailian.console.aliyun.com/cn-beijing/?tab=model#/efm/coding_plan)。可用模型请参考 Coding Plan [支持的模型](https://help.aliyun.com/zh/model-studio/coding-plan)。

```
{
    "env": {
        "ANTHROPIC_AUTH_TOKEN": "YOUR_API_KEY",
        "ANTHROPIC_BASE_URL": "https://coding.dashscope.aliyuncs.com/apps/anthropic",
        "ANTHROPIC_MODEL": "qwen3.6-plus",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3.6-flash",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3.6-plus",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen3.6-plus",
        "CLAUDE_CODE_SUBAGENT_MODEL": "qwen3.6-plus"
    }
}
```

### 按量计费

将 YOUR\_API\_KEY 替换为[阿里云百炼 API Key](https://help.aliyun.com/zh/model-studio/get-api-key)。可用模型请参考[支持的模型](https://help.aliyun.com/zh/model-studio/anthropic-api-messages#07833dedefft7)。

`ANTHROPIC_BASE_URL` 按地域设置，API Key 需与所选地域对应：

- 华北2（北京）：`https://dashscope.aliyuncs.com/apps/anthropic`

- 新加坡：`https://dashscope-intl.aliyuncs.com/apps/anthropic`

```
{
    "env": {
        "ANTHROPIC_AUTH_TOKEN": "YOUR_API_KEY",
        "ANTHROPIC_BASE_URL": "https://dashscope.aliyuncs.com/apps/anthropic",
        "ANTHROPIC_MODEL": "qwen3.6-plus",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3.6-flash",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3.6-plus",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen3.6-plus",
        "CLAUDE_CODE_SUBAGENT_MODEL": "qwen3.6-plus"
    }
}
```

## **验证配置**

保存配置后，打开新的终端窗口，运行以下命令验证接入是否成功：

```
claude "你好"
```

模型正常返回响应即配置成功。

运行 `claude` 可进入交互模式，支持多轮对话、文件编辑和命令执行，详见 [Claude Code 官方文档](https://code.claude.com/docs/en/overview)。

## **Claude Code IDE 插件**

完成上述 CLI 配置后，可在 IDE 中安装 Claude Code 插件，直接复用 `settings.json` 中的配置。

### VS Code

1. 在扩展市场中搜索 `Claude Code for VS Code` 并安装。

2. 重启 VS Code，点击右上角图标进入 Claude Code。

3. 在对话框中输入 `/`，选择 General config，在 Selected Model 中设置模型。

### JetBrains

1. 在扩展市场中搜索 `Claude Code` 并安装。

2. 重启 IDE，点击右上角图标即可使用。

## **常见问题**

### 错误码

配置过程中遇到报错，请参考对应计费方案的常见问题文档：

- 按量付费：[Anthropic API兼容 - 错误码](https://help.aliyun.com/zh/model-studio/anthropic-api-messages#7d8d58d0736zv)

- Coding Plan：[Coding Plan 常见问题](https://help.aliyun.com/zh/model-studio/coding-plan-faq)

- Token Plan 团队版：[Token Plan 团队版常见问题](https://help.aliyun.com/zh/model-studio/token-plan-faq)

### 启动 Claude Code 后，界面显示"Unable to connect to Anthropic services. Failed to connect to api.anthropic.com: ERR\_BAD\_REQUEST"

该错误表示 Claude Code 尝试连接 Anthropic 官方服务而非阿里云百炼服务端，通常是因为环境变量未正确配置或未生效。请按以下步骤排查：

1. **检查配置**：启动 Claude Code 后，执行 `/status` 命令，确认 `ANTHROPIC_BASE_URL` 和 `ANTHROPIC_AUTH_TOKEN` 的值是否正确指向百炼地址。如果输出为空或指向非百炼地址，请检查 `settings.json` 配置是否正确。

2. **确认 hasCompletedOnboarding**：检查 `~/.claude.json` 文件中 `hasCompletedOnboarding` 是否设置为 `true`，否则 Claude Code 启动时会尝试连接 Anthropic 官方服务进行登录验证。

3. **重新打开终端**：修改配置文件后，需要打开一个新的终端窗口，再执行 `claude` 命令以使配置生效。

### 使用旧版接口，切换模型不生效

旧版兼容接口 `https://dashscope.aliyuncs.com/api/v2/apps/claude-code-proxy` 仅支持 `qwen3-coder-plus` 模型，指定其他模型不会生效。如需调用其他模型，请按本文配置迁移至新版接口。
