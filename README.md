# Tegridy-AI-TRPG

AI 主持的桌面角色扮演游戏。

> ⚠️ **当前状态：内部开发阶段** — 功能尚未稳定，API 和玩法随时可能变更，暂不对外发布。

## 简介

这是一个用自然语言游玩的 TTRPG（桌面角色扮演游戏）。你只需要描述角色想做什么，幕后的多 Agent 系统会自动完成规则裁判、效果推演和叙事生成，把结果以沉浸式叙事的方式呈现给你。

**你只管说人话，规则的事交给 AI。**

核心规则融合了 PBTA（Powered by the Apocalypse）骨架与《异景 / Otherscape》机制。

## 技术栈

- **语言**: Python 3.11+
- **LLM**: DeepSeek（OpenAI 兼容接口）
- **依赖**: `openai`、`python-dotenv`

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repo-url>
cd Tegridy-AI-TRPG

# 创建并激活虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API Key

项目里有个 `.env.example` 文件，把它复制一份，改名为 `.env`。

打开 `.env` 文件，里面只有三行：

```
DEEPSEEK_API_KEY=你的API密钥填这里
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

你需要做的：把 `DEEPSEEK_API_KEY=` 后面的内容替换成你自己的 DeepSeek API 密钥。另外两行一般不用改。

> 💡 API 密钥可以在 [DeepSeek 开放平台](https://platform.deepseek.com/) 注册并获取。如果你用的不是 DeepSeek 官方 API（比如第三方代理），记得把 `DEEPSEEK_BASE_URL` 也改成对应的地址。

### 3. 运行

```bash
python main.py
```

## 游戏中

输入你的行动描述，按回车提交。例如：

```
> 我拔出剑冲向门口的守卫
> 我试图说服酒保透露密道的位置
> 我仔细观察房间里有没有暗门
```

### 命令

| 命令 | 说明 |
|------|------|
| `/help` | 查看帮助 |
| `/debug` | 切换调试模式 |
| `/quit` | 退出游戏 |

## 开发

```bash
# 代码质量检查
ruff check .
ruff format .

# 运行测试
python -m unittest discover -s tests
```

更多开发约定和设计原则见 [AGENTS.md](AGENTS.md)。

## License

内部开发中，暂未确定。
