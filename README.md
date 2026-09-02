# DS Chat Parser

将从 DeepSeek 官方网页导出的会话文件解析为清晰易读的文本文件。

## 📌 项目简介

DS Chat Parser 是一款图形化桌面工具，用于解析 DeepSeek 官方导出的 JSON 格式会话记录，并将其转换为结构清晰、易于阅读的文本文件。适用于聊天记录备份、分享、打印或迁移至其他 AI 对话场景。

## ✨ 主要功能

- **灵活导出策略**：支持将会话合并为单个文件，或每个会话单独导出为一个文件
- **自定义导出内容**：可选择是否包含 AI 思考链、AI 搜索资料、用户引用文件、消息时间戳等
- **自定义缩进风格**：支持无缩进、双空格、加号、减号等多种缩进方式
- **自定义发言人代称**：可将 "User" / "AI" 替换为自定义名称
- **图形化界面**：基于 PySide6 构建，操作直观，无需命令行

## 🖼️ 效果预览

> 你可以在 Release 页面下载后直接运行体验。
## 📦 下载与使用

### 获取程序

请前往 [Releases](https://github.com/Polaris-light/DS_Chat_Parser/releases) 页面下载最新版本：
- 推荐下载 `ds_chat_parser_v1.0.0.zip`，解压后双击 `ds_chat_parser.exe` 即可运行
- 压缩包内附 `使用说明.txt`，建议首次使用时先阅读

### 使用步骤

1. 导入 从DeepSeek官方网页端 导出的 `conversations.json` 文件
2. 点击“解析”按钮，加载会话列表
3. 勾选需要导出的会话
4. 选择导出位置和格式（当前支持 TXT）
5. 根据需要调整配置项（缩进、发言人代称、导出内容等）
6. 点击“导出”按钮，程序自动处理

### 如何获取 `conversations.json` 文件？
1. 访问deepseek官方网页端 https://chat.deepseek.com/ 并登录
2. 点击左下角"..." → 系统设置 → 数据管理
3. 点击"导出所有历史对话" → 导出（或重新导出）
4. 点击"下载"获取 zip 文件，解压后 conversations.json 即为所需文件

## 🛠️ 从源码构建（可选）

如果你希望自行构建或二次开发，请确保已安装 Python 3.11+ 和 Poetry/pip，然后执行：

```bash
# 克隆仓库
git clone https://github.com/Polaris-light/DS_Chat_Parser.git
cd DS_Chat_Parser

# 安装依赖（推荐使用虚拟环境）
pip install -r requirements.txt

# 运行程序
python main.py