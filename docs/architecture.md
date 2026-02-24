# Architecture

详细架构与 workflow 请看：

- [Workflow Deep Dive](./workflow.md)

本文档保留高层摘要，方便快速定位。

## Goal
给定消费场景，返回净收益最高的卡：

`net_reward = cashback - transaction_fee - optional_annual_fee_proration`

## Layers
- API Layer: FastAPI routes (`/health`, `/recommend`)
- Agent Layer: orchestration between parser, engine, retriever
- Engine Layer: deterministic reward calculation
- Data Layer: JSON policy store (future: DB)
- RAG Layer: evidence retrieval placeholder (future: vector DB)
- Integration Layer: Telegram bot

## Principles
- 计算结果以结构化规则引擎为准
- RAG 仅用于解释与溯源
- 先做可测的 deterministic MVP，再逐步替换为生产级组件
