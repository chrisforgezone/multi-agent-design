# AI 知识库系统 — 项目愿景 v2

## 做什么

### 信息源（6 个）

| 来源 | 获取方式 | 每日候选数 |
|---|---|---|
| arXiv | 官方 API（cs.AI, cs.CL） | 30 条 |
| Hacker News | Firebase API `/v0/topstories` | 30 条 |
| Reddit | r/MachineLearning + r/LocalLLaMA RSS | 各子版默认 25 条，不翻页 |
| GitHub Trending | GitHub API（日榜优先，无命中回退周榜） | 30 条 |
| LangChain Blog | 原生 RSS | 2 条，不过滤热度 |
| Anthropic Research Blog | 原生 RSS | 2 条，不过滤热度 |

### 产出

- 每天 19:00 定时抓取，筛选并生成 **20 条**知识条目
- 输出为 `/output/kb_YYYY_MM_DD.md`，每天新建文件，不覆盖
- 若全天无匹配内容，生成兜底文件，内容为 `今天没有什么好看的`

---

## 筛选规则

### 关键词匹配

**Tier 1 — 命中任一即入选：**

| 方向 | 关键词 |
|---|---|
| Agent | `agentic`, `multi-agent`, `AI agent`, `LLM agent`, `agent workflow`, `agent system`, `agent architecture`, `autonomous agent` |
| Harness | `agent harness`, `agent framework`, `agent orchestration`, `LLM framework` |
| Skill | `MCP`, `Model Context Protocol`, `tool use`, `tool calling`, `function calling`, `plugin system` |
| Context | `context window`, `context management`, `long context`, `token limit`, `RAG`, `retrieval augmented` |
| Memory | `LLM memory`, `agent memory`, `vector memory`, `working memory`, `episodic memory`, `persistent memory` |

**Tier 2 — 次级信号（标题+摘要中命中 ≥2 个才入选）：**

`chain of thought`, `tree of thoughts`, `ReAct`, `reflexion`, `planning+LLM`, `agent debugging`, `agent evaluation`, `prompt caching`, `embedding`, `knowledge graph`, `vector database`

**排除关键词（强过滤）：**

`travel agent`, `real estate agent`, `insurance agent`, `sports agent`, `chemical agent`, `biological agent`, `customer support agent`

### arXiv 特殊规则

- 未匹配 Tier 1 关键词但来自**权威机构**的论文直接纳入（每日期限 ≤ 3 篇）
- 权威机构白名单：OpenAI, DeepMind, Anthropic, Meta AI, Google Research, Microsoft Research, Nvidia Research, Apple, Stanford, MIT, CMU, Berkeley, Princeton, Toronto, Montreal (MILA)

### GitHub Trending 特殊规则

- 先取日榜；日榜无匹配关键词的仓库，回退取周榜
- 以仓库 README + 描述 + topics 字段做关键词匹配

---

## 热度排序（归一化）

### 基准值

| 来源 | 原始热度 | 固定基准值 | 归一化公式 |
|---|---|---|---|
| HN | upvotes | 300 | `upvotes / 300` |
| Reddit | upvotes | 200 | `upvotes / 200` |
| GitHub | stars_gained_that_day | 150 | `stars_gained / 150` |

### 无热度值处理

- arXiv 权威机构论文、LangChain/Anthropic 博客 无热度指标，直接放到排序末尾，内部按时间倒序排列
- 同热度并列：按时间倒序

---

## 去重

- 同一文章跨源出现，合并保留最先出现的来源下，其他来源附加标注
- 去重依据：URL 精确匹配 + 标题相似度（余弦 ≥ 0.9 视为重复）

---

## 知识条目字段

| 字段 | 说明 |
|---|---|
| 标题 | 原文标题 |
| 原文链接 | 文章 URL |
| 来源 | arXiv / Hacker News / Reddit / GitHub / LangChain Blog / Anthropic |
| 发布日期 | 原文发布日期 |
| 标签 | 所属方向：Agent / Harness / Skill / Context Manager / Memory |
| 热度 | 原始热度值（若有） |
| AI 摘要 | DeepSeek V4 Pro 生成，正文用英文，其他要素可用中文 |

### AI 摘要内容模板

1. **一句话概述**（What is this about）
2. **核心观点**（3-5 key points）
3. **与关注方向的关联**（Why Agent/Harness/Skill/Context Manager/Memory practitioners should care）
4. **技术方法简述**（Methods / architecture used）
5. **代码可复现性**（Open source? Runnable?）
6. **新方法论 / 工程思想 / 最佳实践**（Novel methodology, engineering ideas, or best practices）

---

## 不做什么

- 不使用第三方 RSS 桥接服务（RSSHub 等），直接调用官方 API 或原生 RSS
- 不发送邮件，摘要直接输出到本地 `/output/` 目录

---

## 技术实现

| 项 | 决策 |
|---|---|
| 语言 | Python |
| 大模型 | DeepSeek V4 Pro（API 就绪） |
| 配置 | 写入配置文件（API 密钥、关键词、配额、基准值等），不便编码 |
| 触发 | cron 定时任务，每日 19:00 执行 |
| 容错 | 单体源失败跳过，其余正常执行；最终条目数不足 20 不影响输出 |

---

## 验收标准

1. `bash` 执行抓取脚本，验证 `/output/kb_YYYY_MM_DD.md` 正常生成
2. 文件内知识条目信息完整，涵盖全部 7 个字段
3. 摘要包含 6 项内容要素
4. 热度排序正确，无热度条目位于末尾（时间倒序）
5. 关键词过滤有效，排除词命中条目不出现在结果中
6. 无匹配时生成兜底文件
7. 跨源重复文章被正确合并
