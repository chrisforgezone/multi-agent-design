# AGENTS.md — AI 知识库系统

> 严格对齐 `knowledge-base/spec/project-vision-v2.md` 的每一条款。

---

## 1. 信息源抓取

### 1.1 arXiv（官方 API）

- 调用 `http://export.arxiv.org/api/query`，分类限定 `cs.AI` 和 `cs.CL`
- 每次拉取 **30 条**最新论文
- `sortBy=submittedDate`, `sortOrder=descending`, `max_results=30`
- 解析返回的 Atom XML，提取：标题、摘要、arxiv_id、发布日期、作者机构

### 1.2 Hacker News（Firebase API）

- 调用 `https://hacker-news.firebaseio.com/v0/topstories.json` 获取 top 100 ID
- 逐条调用 `/v0/item/{id}.json` 获取标题、URL、score、时间，直到攒满 **30 条**有 URL 的条目
- 遇到无 URL 的条目（Ask HN / 纯文本）跳过

### 1.3 Reddit（RSS）

- 地址：`https://www.reddit.com/r/MachineLearning/.rss`、`https://www.reddit.com/r/LocalLLaMA/.rss`
- 每个子版 RSS 返回默认 25 条，**不分页**
- 两个子版 RSS 合并去重后作为候选池
- 解析 RSS `<entry>`，提取标题、链接、摘要、发布时间、score（若有）

### 1.4 GitHub Trending（GitHub API）

- **先取日榜**：`https://api.github.com/search/repositories?q=created:>{today}&sort=stars&order=desc&per_page=30`
- **日榜匹配失败时回退周榜**：时间窗口扩大到 7 天
- 匹配字段：**README 内容 + repo.description + repo.topics**
- 若日榜 ≥ 1 个匹配关键词的仓库，不再查周榜

### 1.5 LangChain Blog（原生 RSS）

- 直接请求 LangChain Blog RSS 地址，不做热度过滤
- 每日固定 **2 条**最新文章

### 1.6 Anthropic Research Blog（原生 RSS）

- 直接请求 Anthropic Research Blog RSS 地址，不做热度过滤
- 每日固定 **2 条**最新文章

### 容错规则

- 任意源请求失败或超时（建议 30s 超时）→ 记录 error 日志后跳过该源
- 其余源正常继续，最终条目不足 20 不影响输出
- **不使用任何第三方 RSS 桥接服务**（RSSHub 等）

---

## 2. 关键词筛选

### 2.1 Tier 1（命中任一即入选）

| 方向 | 关键词（不区分大小写） |
|---|---|
| Agent | `agentic`, `multi-agent`, `AI agent`, `LLM agent`, `agent workflow`, `agent system`, `agent architecture`, `autonomous agent` |
| Harness | `agent harness`, `agent framework`, `agent orchestration`, `LLM framework` |
| Skill | `MCP`, `Model Context Protocol`, `tool use`, `tool calling`, `function calling`, `plugin system` |
| Context | `context window`, `context management`, `long context`, `token limit`, `RAG`, `retrieval augmented` |
| Memory | `LLM memory`, `agent memory`, `vector memory`, `working memory`, `episodic memory`, `persistent memory` |

- 匹配范围为：**标题 + 摘要/正文摘要**

### 2.2 Tier 2（标题+摘要中命中 ≥ 2 个才入选）

关键词清单（不区分大小写）：
`chain of thought`, `tree of thoughts`, `ReAct`, `reflexion`, `planning+LLM`, `agent debugging`, `agent evaluation`, `prompt caching`, `embedding`, `knowledge graph`, `vector database`

### 2.3 排除关键词（强过滤）

命中以下任一**直接丢弃**（不区分大小写）：
`travel agent`, `real estate agent`, `insurance agent`, `sports agent`, `chemical agent`, `biological agent`, `customer support agent`

### 2.4 筛选顺序

1. 先用排除关键词过滤
2. 再用 Tier 1 匹配
3. 未命中 Tier 1 的用 Tier 2 匹配（计数 ≥ 2 才保留）
4. arXiv 额外走权威机构逻辑（见 2.5）

### 2.5 arXiv 权威机构规则

> 仅适用于 arXiv，不适用于其他来源。

- 未命中 Tier 1 关键词但作者机构命中以下白名单的论文 → 直接纳入
- 每个日期限 **≤ 3 篇**，超出按发布时间倒序取前 3

**权威机构白名单：**
`OpenAI`, `DeepMind`, `Anthropic`, `Meta AI`, `Google Research`, `Microsoft Research`, `Nvidia Research`, `Apple`, `Stanford`, `MIT`, `CMU`, `Berkeley`, `Princeton`, `Toronto`, `Montreal`, `MILA`

- 机构匹配方式：在 arXiv 论文的 `<author><affiliation>` 字段中搜索白名单关键词（不区分大小写）

---

## 3. 去重

### 3.1 去重依据

1. **URL 精确匹配**：相同 URL → 视为重复
2. **标题相似度**：对无 URL 或 URL 不同的条目，计算标题余弦相似度 ≥ **0.9** → 视为重复

### 3.2 合并规则

- 保留**最先出现**的那个来源的条目
- 在被合并条目的来源字段后追加标注，如 `Hacker News, Reddit`
- 合并后的条目取各源热度中的最大值

### 3.3 去重顺序

按抓取顺序执行去重（即 arXiv → HN → Reddit → GitHub → LangChain → Anthropic），先出现的源优先保留。

---

## 4. 热度计算与排序

### 4.1 归一化公式

| 来源 | 原始热度 | 固定基准值 | 公式 |
|---|---|---|---|
| Hacker News | `score`（upvotes） | 300 | `score / 300` |
| Reddit | `score`（upvotes） | 200 | `score / 200` |
| GitHub | 当日新增 star 数 | 150 | `stars_gained / 150` |

- 归一化值 > 1.0 的情况：正常保留（不截断），用于跨源比较
- LangChain/Anthropic/arXiv 权威机构条目：无归一化值，标记为 `no_score`

### 4.2 排序规则

1. 有归一化值的条目 → 按归一化值**从高到低**排列
2. 无归一化值的条目 → 排在所有有值条目**末尾**
3. 无归一化值内部 → 按原文发布日期**倒序**（新的在前）
4. 归一化值相同 → 按原文发布日期**倒序**

---

## 5. AI 摘要生成

### 5.1 模型

- DeepSeek V4 Pro，API 就绪
- 每篇文章调用一次生成摘要

### 5.2 摘要内容模板（英文正文，其他要素可用中文）

每条摘要必须包含 6 项：

1. **One-sentence overview**（一句话概述 — 这是讲什么的）
2. **Key points**（3-5 个核心观点）
3. **Relevance to focus areas**（为什么关注 Agent/Harness/Skill/Context Manager/Memory 的人应该看）
4. **Technical methods**（用了什么方法/架构）
5. **Code reproducibility**（是否开源、能否复现/跑起来）
6. **Novel methodology / engineering ideas / best practices**（提出了什么新方法论、工程思想或最佳实践）

### 5.3 Prompt 要求

- 输入：文章标题 + 原文摘要/标签/描述
- 输出语言：摘要正文用**英文**
- 标签字段（第 2.1 节 5 个方向）可以选择用中文标注

---

## 6. 知识条目字段

每条输出必须包含全部 7 个字段：

| # | 字段 | 来源 |
|---|---|---|
| 1 | 标题 | 原文标题（保留原始语言） |
| 2 | 原文链接 | 文章 URL |
| 3 | 来源 | 取值：`arXiv` / `Hacker News` / `Reddit` / `GitHub` / `LangChain Blog` / `Anthropic` |
| 4 | 发布日期 | 原文发布日期（YYYY-MM-DD） |
| 5 | 标签 | 一个或多个：`Agent` / `Harness` / `Skill` / `Context Manager` / `Memory` |
| 6 | 热度 | 原始热度值（upvotes/stars），若无则为 `-` |
| 7 | AI 摘要 | DeepSeek V4 Pro 生成，正文英文，6 要素 |

---

## 7. 输出文件

### 7.1 文件路径与命名

- 输出目录：`/output/`
- 文件名格式：`kb_YYYY_MM_DD.md`
- 每天一个新文件，**不覆盖**历史文件

### 7.2 文件内格式

```markdown
# AI Knowledge Brief - 2026-05-20

(共 N 条)

---

## 1. [标题](原文链接)
- **来源**: 来源名称
- **发布日期**: YYYY-MM-DD
- **标签**: Agent, Skill
- **热度**: 120 upvotes (归一化: 0.40)

### 摘要
(AI 生成的摘要正文)

---

## 2. [标题](原文链接)
...
```

- 条目按热度排序（见第 4 节）
- 无热度条目末尾标注 `(无热度数据)`

### 7.3 兜底规则

- 若全天所有源筛选+去重后结果为 0 条：
  - 仍然创建文件 `kb_YYYY_MM_DD.md`
  - 文件内容仅一行：`今天没有什么好看的`

---

## 8. 配置管理

全部可配置项写入**配置文件**（如 `config.yaml`），不便编码：

| 配置项 | 内容 |
|---|---|
| API 密钥 | DeepSeek API key, GitHub token |
| 关键词 | Tier 1 / Tier 2 / 排除关键词完整清单 |
| 基准值 | 归一化固定值（300 / 200 / 150） |
| 每日配额 | 各源候选数（30/30/25/30/2/2）、输出总数（20） |
| 权威机构白名单 | arXiv 特殊规则机构清单 |
| 超时与重试 | 请求超时秒数 |
| 输出目录 | 默认 `/output/` |
| cron 配置 | `0 19 * * *`（每日 19:00） |

---

## 9. 定时与触发

- **cron 表达式**：`0 19 * * *`
- 指向项目入口脚本（Python）
- 手动执行入口脚本也应产出相同结果

---

## 10. 验收检查清单

实现完成后必须逐条通过：

- [ ] **1.** `bash` 执行脚本后 `/output/kb_YYYY_MM_DD.md` 正常生成
- [ ] **2.** 文件内每条知识条目包含全部 7 个字段（标题、链接、来源、发布日期、标签、热度、AI 摘要）
- [ ] **3.** 每条 AI 摘要包含 6 项内容要素（概述、核心观点、关联方向、技术方法、可复现性、新方法论）
- [ ] **4.** 热度排序正确：有值条目按归一化分降序，无值条目在末尾按时间倒序
- [ ] **5.** 排除关键词有效：命中 `travel agent` 等词条的条目不出现在结果中
- [ ] **6.** 无匹配内容时生成兜底文件，内容为 `今天没有什么好看的`
- [ ] **7.** 跨源重复文章被正确合并，同一 URL 或相似标题只出现一次

---

## 11. 实现顺序建议

1. 配置文件（`config.yaml`）
2. 各源抓取模块（独立函数，统一返回 `List[dict]` 格式）
3. 关键词筛选模块（Tier 1 → Tier 2 → 排除词 → arXiv 权威机构）
4. 去重模块（URL 精确 + 标题余弦相似度）
5. 热度计算与排序模块
6. DeepSeek 摘要生成模块
7. Markdown 输出模块
8. 主流程 orchestration 脚本
9. cron 集成
10. 验收测试（对照第 10 节逐条验证）
