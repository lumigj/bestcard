# BestCard Architecture Workflow Deep Dive

本文档详细说明当前代码的真实执行链路、数据结构、异常路径和扩展位点。

## 1. Scope And Current State

当前仓库是一个可运行的 MVP，目标是：
- 输入消费场景（自然语言或结构化参数）
- 用确定性规则引擎计算每张卡净收益
- 返回最优卡和排序结果
- 附带政策证据片段（当前为规则拼接，不是向量检索）

当前能力边界（重要）：
- 已支持：按 category rate + foreign fee + 年费按月摊销（可选）计算净收益
- 未支持：跨交易累计封顶、季度激活状态、MCC 精细归类、真实向量 RAG 检索

## 2. Module Map (By File)

| Layer | Responsibility | File |
|---|---|---|
| API | HTTP 服务入口、路由注册 | `src/bestcard/api/app.py` |
| API Route | `/recommend` 请求接入与错误映射 | `src/bestcard/api/routes/recommend.py` |
| Orchestrator | 串联 parser / repository / engine / rag | `src/bestcard/agents/orchestrator.py` |
| NLP Parser | 从自然语言提取 amount/category/is_foreign | `src/bestcard/nlp/parser.py` |
| Repository | 读取 JSON 卡政策并校验成模型 | `src/bestcard/repository/policy_store.py` |
| Engine | 单卡打分与全卡排序 | `src/bestcard/engine/evaluator.py`, `selectors.py` |
| RAG (placeholder) | 返回解释片段 | `src/bestcard/rag/retriever.py` |
| Domain Models | 领域模型定义 | `src/bestcard/domain/models.py` |
| Schemas | API 入参与出参模型 | `src/bestcard/schemas/requests.py`, `responses.py` |
| Telegram | Bot 消息入口与回复格式 | `src/bestcard/integrations/telegram_bot.py` |
| Config | 环境变量配置 | `src/bestcard/config.py` |

## 3. End-To-End Workflow (HTTP /recommend)

### 3.1 Runtime Initialization

进程启动时（`main.py -> bestcard.api.app:run`）：
1. FastAPI app 被创建，注册 `/health` 与 `/recommend`。
2. 导入 `api/routes/recommend.py` 时，模块级对象被初始化：
3. `orchestrator = RecommendationOrchestrator(PolicyStore(settings.card_policy_file))`
4. 所以每个请求复用同一个 orchestrator 实例，但卡数据会在每次请求时重新读取文件。

### 3.2 Request Path

请求到 `POST /recommend` 后，执行顺序如下：
1. FastAPI 将 JSON 反序列化为 `RecommendRequest`（Pydantic 校验）。
2. 路由函数 `recommend(request)` 调用 `orchestrator.recommend(request)`。
3. orchestrator 先 `_build_scenario(request)`，构建 `SpendScenario`。
4. `policy_store.load_cards()` 从 JSON 文件加载 `list[CardPolicy]`。
5. `rank_cards(cards, scenario)` 对每张卡执行 `evaluate_card` 并排序。
6. 取排序第一名 `best`，再根据 `best.card_id` 找到对应 `CardPolicy`。
7. `retrieve_policy_evidence(best_card_policy, scenario.category)` 生成政策证据片段。
8. 组装 `RecommendResponse` 返回。
9. 任一步抛异常会被路由捕获，统一映射为 HTTP 400（`detail` 为异常字符串）。

### 3.3 Sequence Diagram

```text
Client
  -> FastAPI /recommend
  -> route.recommend()
  -> orchestrator.recommend()
  -> orchestrator._build_scenario()
     -> parse_scenario() [if message exists]
  -> policy_store.load_cards()
  -> rank_cards()
     -> evaluate_card(card_1)
     -> evaluate_card(card_2)
     -> ...
  -> retrieve_policy_evidence(best_card)
  <- RecommendResponse(best_card, ranked_cards, parsed_scenario, policy_evidence)
<- HTTP 200 JSON
```

## 4. Scenario Parsing Workflow (NLP Layer)

文件：`src/bestcard/nlp/parser.py`

### 4.1 Input Precedence

`parse_scenario(...)` 的优先级：
1. `amount` 参数若显式传入，优先于文本抽取。
2. `category` 参数若显式传入，优先于关键词识别。
3. `is_foreign` 参数若显式传入，优先于关键词识别。

### 4.2 Amount Extraction

规则：
- 正则：`(\d+(?:\.\d+)?)\s*(?:usd|\$|刀|块|元)?`
- 只取第一个匹配数值
- 未匹配或 `<=0` 抛 `ScenarioParseError`

影响：
- 文本包含多个金额时，只会使用第一个（例如“机票500酒店300”会取 500）。
- 不识别千分位写法（例如 `1,200`）和货币代码变体（如 `US$`）。

### 4.3 Category Extraction

关键词字典匹配顺序：
1. grocery
2. dining
3. travel
4. gas
5. online_shopping

匹配逻辑：
- `lower()` 后按字典顺序检查关键词子串
- 命中即返回对应 category
- 都不命中返回 `"other"`

### 4.4 Foreign Detection

若文本包含以下任一关键词，`is_foreign=True`：
- `境外`, `海外`, `international`, `abroad`, `foreign`

## 5. Deterministic Evaluation Workflow (Engine Layer)

文件：`src/bestcard/engine/evaluator.py`, `selectors.py`

### 5.1 Per-Card Evaluation

`evaluate_card(card, scenario)` 步骤：
1. `_category_rate(card, scenario.category)`：
2. 遍历 `card.reward_rules`，按 `rule.category.lower() == scenario.category.lower()` 精确匹配
3. 命中则使用 `rule.cashback_rate`
4. 否则回退 `card.base_cashback_rate`
5. `cashback = scenario.amount * rate`
6. `fee` 初始为 0
7. 若 `scenario.is_foreign`，加 `scenario.amount * card.foreign_txn_fee_rate`
8. 若 `include_annual_fee_proration` 且 `monthly_spend_estimate` 有值，额外加 `card.annual_fee / 12`
9. `net_reward = cashback - fee`
10. 输出 `CardEvaluation`（包含 reasoning 字符串）

### 5.2 Sorting And Selection

`rank_cards(cards, scenario)`：
1. 对每张卡调用 `evaluate_card`
2. 按 `(net_reward, cashback)` 降序排序
3. 返回排序列表，`ranked[0]` 即最优

排序行为说明：
- 第一排序键是净收益，确保“cashback 高但 fee 更高”的卡不会误选。
- 同净收益时比较 cashback，cashback 高者优先。
- Python 排序稳定，若两者两键都相同，保留原输入顺序。

### 5.3 Formula Summary

```text
effective_rate = matched_category_rate or base_cashback_rate
cashback = amount * effective_rate
fee = (is_foreign ? amount * foreign_txn_fee_rate : 0)
    + (include_annual_fee_proration and monthly_spend_estimate ? annual_fee / 12 : 0)
net_reward = cashback - fee
```

## 6. Evidence Workflow (Current RAG Placeholder)

文件：`src/bestcard/rag/retriever.py`

当前并非向量检索，而是“根据最优卡规则拼接文本片段”：
1. 遍历最优卡 `reward_rules`，找 category 命中的规则
2. 生成片段：`{card_name}: {category} cashback {rate}`
3. 若该规则有 `cap_amount + cap_period`，追加封顶描述
4. 若外币手续费 > 0，追加外币手续费片段
5. 若有 notes，追加 notes 片段
6. 最多返回 3 条

设计意图：
- 先确保计算正确和可解释
- 以后替换成真正的向量召回时，不改变 orchestrator 输出结构

## 7. Data Contracts

### 7.1 Card Policy JSON

来源：`data/cards/sample_cards.json`  
加载模型：`CardPolicy`

关键字段：
- `card_id`: 稳定唯一 ID（系统内主键语义）
- `card_name`: 展示名
- `annual_fee`: 年费（数值）
- `foreign_txn_fee_rate`: 外币手续费率（如 `0.03` = 3%）
- `base_cashback_rate`: 非命中类别时兜底返现率
- `reward_rules[]`: 分类返现规则
- `notes`: 自由文本备注

### 7.2 API Request (`RecommendRequest`)

字段语义：
- `message`: 自然语言描述（可选）
- `amount` + `category`: 结构化输入（可选，但若无 message 则必须提供）
- `is_foreign`: 是否境外消费（可选）
- `currency`: 币种字符串（当前只透传，不参与换汇计算）
- `include_annual_fee_proration`: 是否计入单次推荐中的年费摊销
- `monthly_spend_estimate`: 与上项联动，存在时才计入 `annual_fee/12`

校验约束：
- 若无 `message`，必须有 `amount` 和 `category`
- `SpendScenario.amount` 必须 `>0`

### 7.3 API Response (`RecommendResponse`)

- `best_card`: 最优卡评分结果
- `ranked_cards`: 全部卡排序结果
- `parsed_scenario`: 最终参与计算的结构化场景
- `policy_evidence`: 解释片段

### 7.4 Example

Request:
```json
{
  "message": "今晚在超市花200刀，哪张卡最好？"
}
```

Response:
```json
{
  "best_card": {
    "card_id": "blue_cash_plus",
    "card_name": "Blue Cash Plus",
    "cashback": 8.0,
    "fee": 0.0,
    "net_reward": 8.0,
    "reasoning": "rate=4.00% (matched category 'grocery'), cashback=8.00, fee=0.00, net=8.00"
  },
  "ranked_cards": [
    "... omitted ..."
  ],
  "parsed_scenario": {
    "amount": 200.0,
    "category": "grocery",
    "is_foreign": false,
    "currency": "USD",
    "include_annual_fee_proration": false,
    "monthly_spend_estimate": null
  },
  "policy_evidence": [
    "Blue Cash Plus: grocery cashback 4%",
    "Blue Cash Plus: foreign transaction fee 3.0%",
    "Policy note: 4% grocery up to yearly cap; 3% online shopping; 2% dining."
  ]
}
```

## 8. Telegram Workflow

文件：`src/bestcard/integrations/telegram_bot.py`

启动流程：
1. 读取 `TELEGRAM_BOT_TOKEN`
2. 注册 `/start` 和文本消息 handler
3. `run_polling()` 持续拉取消息

消息流程：
1. 用户发送自然语言消息
2. `handle_message` 构造 `RecommendRequest(message=text)`
3. 调用同一个 orchestrator（与 HTTP 用同样业务链）
4. `_format_reply` 输出：
5. 最优卡名
6. 净收益（拆分 cashback/fee）
7. 场景摘要（amount/category）
8. Evidence 列表

错误路径：
- 任意异常被捕获后返回 `Parse failed: <error>`

## 9. Failure And Error Mapping

| Failure | Source | Current Behavior |
|---|---|---|
| 文本无法解析金额 | `parse_scenario` | 抛 `ScenarioParseError`，HTTP 400 / Telegram parse failed |
| 无 message 且缺 amount/category | `orchestrator._build_scenario` | 抛 `ValueError`，HTTP 400 |
| 卡政策文件不存在 | `PolicyStore.load_cards` | 抛 `FileNotFoundError`，HTTP 400 |
| JSON 结构不合法 | `CardPolicy.model_validate` | 抛 Pydantic 异常，HTTP 400 |
| 卡列表为空 | `orchestrator.recommend` | 抛 `ValueError(\"No cards available.\")`，HTTP 400 |

## 10. Performance Characteristics

当前复杂度：
- `N` 张卡，每次请求约 `O(N * R)`，`R` 是每张卡规则数
- 读卡策略文件是每请求一次 I/O（没有内存缓存）

当前 MVP 规模下足够；若扩展到多用户高并发，建议：
- 在进程内缓存卡政策并支持热更新
- 把 policy 存储迁移到数据库
- parser 与 engine 保持纯函数，便于并行和测试

## 11. RAG Ingest Workflow (Offline)

文件：`src/bestcard/rag/ingest.py`

当前离线流程：
1. 读取 `data/rag/raw/*`
2. 逐文件复制写入 `data/rag/chunks/*.chunk.txt`
3. 输出 ingest 数量

注意：这是占位流程，不包含 embedding 和向量写入。  
未来替换点：
- chunker
- embedding model
- vector store upsert
- retrieval rerank

## 12. Extension Playbook (Where To Change)

如果你要进入生产级实现，建议按下面顺序改：
1. `repository/policy_store.py`
2. 从 JSON 迁移到 DB，并加生效日期、版本字段
3. `engine/evaluator.py`
4. 加入封顶累计、季度激活、point-to-cash 转换规则
5. `nlp/parser.py`
6. 引入 LLM/function-calling 做结构化抽取和澄清问题
7. `rag/retriever.py`
8. 改为向量检索 + 证据段落引用
9. `api/routes/recommend.py`
10. 增加错误分类、trace id、可观测性日志

## 13. Non-Functional Guardrails

建议在下一阶段加上：
- Deterministic tests:
- 每个 category 的回归测试
- 边界值（0/负数/高金额/外币）测试
- Explainability:
- 响应中保留“选卡因子分解”（rate、fee、net）
- Safety:
- 返回里加免责声明（非金融建议）
- Privacy:
- 不保存用户卡号、账单明细等敏感信息

---

如果要继续细化，我建议下一个文档直接写：
- `docs/policy-json-schema.md`（字段、约束、示例、版本迁移规则）
- `docs/engine-rule-spec.md`（可测试的规则规范，不依赖实现细节）
