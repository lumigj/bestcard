# bestcard

根据消费场景自动选择净收益最高（cashback - fee）的信用卡，支持：
- 确定性规则引擎（可测试）
- RAG 证据返回（政策可追溯）
- Telegram 自然语言对话入口

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
python main.py
```

API 启动后：`http://127.0.0.1:8000/docs`

## Project Structure

```text
bestcard/
├─ src/bestcard/
│  ├─ api/                 # FastAPI entry + routes
│  ├─ agents/              # Agent orchestration
│  ├─ domain/              # Core domain models
│  ├─ engine/              # Deterministic card evaluation
│  ├─ integrations/        # Telegram bot integration
│  ├─ nlp/                 # Natural language scenario parser
│  ├─ rag/                 # RAG ingest + retriever placeholders
│  ├─ repository/          # Policy data loading
│  └─ schemas/             # API request/response schemas
├─ data/cards/             # Card policy JSON
├─ data/rag/               # Raw docs + chunks
├─ scripts/                # Utility scripts
├─ tests/                  # Unit tests
└─ docs/                   # Architecture notes
```

## Core Flow

1. 用户输入自然语言消费场景
2. `nlp/parser.py` 解析出 `amount/category/is_foreign`
3. `engine/evaluator.py` 对每张卡计算净收益
4. `engine/selectors.py` 排序后选最优
5. `rag/retriever.py` 返回政策证据片段
6. API 或 Telegram 返回结果

## Next Implementation

- 接入真实 LLM 做更鲁棒的场景抽取
- 政策版本化（生效日期、季度激活状态）
- 对接向量库（pgvector/Qdrant）替换当前占位 RAG
