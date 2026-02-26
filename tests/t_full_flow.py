from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from bestcard import RecommendationOrchestrator
from bestcard import CardPolicy
from bestcard import main as ingest_rag
from bestcard import PolicyStore
from bestcard import RecommendRequest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_POLICY_PATH = PROJECT_ROOT / "data" / "cards" / "sample_cards.json"
RAG_RAW_DIR = PROJECT_ROOT / "data" / "rag" / "raw"
RAG_CHUNK_DIR = PROJECT_ROOT / "data" / "rag" / "chunks"

# Natural language card policy that will be converted by LLM and stored.
CARD_POLICY_DESCRIPTION = """
Card name: Titan Dining Max
Card id: titan_dining_max
Annual fee: 49 USD
Foreign transaction fee: 0%
Base cashback: 1%
Dining cashback: 9%
Travel cashback: 3%
Notes: Strong restaurant card with no foreign transaction fee.
""".strip()

# Natural language spend message for recommendation flow.
SPEND_SCENARIO_MESSAGE = "I will spend 180 USD at a restaurant tonight, which card is best?"


def _normalize_rate(raw_value: float | int | str) -> float:
    value = float(raw_value)
    if value > 1:
        value = value / 100.0
    return value


def _normalize_policy_dict(raw_policy: dict) -> dict:
    raw_policy["annual_fee"] = float(raw_policy.get("annual_fee", 0))
    raw_policy["foreign_txn_fee_rate"] = _normalize_rate(raw_policy.get("foreign_txn_fee_rate", 0))
    raw_policy["base_cashback_rate"] = _normalize_rate(raw_policy.get("base_cashback_rate", 0))

    normalized_rules = []
    for rule in raw_policy.get("reward_rules", []):
        normalized_rule = dict(rule)
        normalized_rule["cashback_rate"] = _normalize_rate(normalized_rule.get("cashback_rate", 0))
        normalized_rules.append(normalized_rule)
    raw_policy["reward_rules"] = normalized_rules

    return raw_policy


def _card_policy_from_natural_language(card_description: str) -> CardPolicy:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required. Install with: pip install -e '.[llm]'") from exc

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Please set it in .env before running this script.")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You extract credit card policy into strict JSON. "
        "Return only one JSON object with keys: card_id, card_name, annual_fee, "
        "foreign_txn_fee_rate, base_cashback_rate, reward_rules, notes. "
        "reward_rules must be an array of {category, cashback_rate, cap_amount, cap_period}. "
        "Use cashback/fee rates as decimals (0.09 means 9%). "
        "Allowed categories: grocery, dining, travel, gas, online_shopping, other."
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": card_description},
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("LLM returned empty content when extracting card policy.")

    raw_policy = json.loads(content)
    normalized_policy = _normalize_policy_dict(raw_policy)
    return CardPolicy.model_validate(normalized_policy)


def _save_policy_with_new_card(new_card: CardPolicy) -> Path:
    if not BASE_POLICY_PATH.exists():
        raise FileNotFoundError(f"Base policy file not found: {BASE_POLICY_PATH}")

    base_cards = json.loads(BASE_POLICY_PATH.read_text(encoding="utf-8"))
    base_cards = [card for card in base_cards if card.get("card_id") != new_card.card_id]
    base_cards.append(new_card.model_dump())

    cards_dir = PROJECT_ROOT / "data" / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        prefix="cards_nl_",
        dir=cards_dir,
        delete=False,
        encoding="utf-8",
    ) as fp:
        json.dump(base_cards, fp, ensure_ascii=False, indent=2)
        return Path(fp.name)


def _save_rag_reference(new_card: CardPolicy, card_description: str) -> Path:
    RAG_RAW_DIR.mkdir(parents=True, exist_ok=True)
    reference_path = RAG_RAW_DIR / f"{new_card.card_id}.txt"
    reference_path.write_text(card_description, encoding="utf-8")
    return reference_path


def _run_rag_ingest_at_project_root() -> None:
    original_cwd = Path.cwd()
    os.chdir(PROJECT_ROOT)
    try:
        ingest_rag()
    finally:
        os.chdir(original_cwd)


def _load_chunk_reference(card_id: str) -> str:
    chunk_path = RAG_CHUNK_DIR / f"{card_id}.chunk.txt"
    if not chunk_path.exists():
        return f"No chunk reference found for card_id={card_id}."

    content = chunk_path.read_text(encoding="utf-8").strip()
    if len(content) > 500:
        return f"{content[:500]}..."
    return content


def t_nl_store_card_rank_and_explain() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    new_card = _card_policy_from_natural_language(CARD_POLICY_DESCRIPTION)
    temp_policy_path = _save_policy_with_new_card(new_card)
    reference_raw_path = _save_rag_reference(new_card, CARD_POLICY_DESCRIPTION)
    _run_rag_ingest_at_project_root()

    orchestrator = RecommendationOrchestrator(PolicyStore(str(temp_policy_path)))
    result = orchestrator.recommend(RecommendRequest(message=SPEND_SCENARIO_MESSAGE))

    chunk_reference = _load_chunk_reference(result.best_card.card_id)

    print("=== Step 1: New Card Stored From Natural Language ===")
    print(f"Card id: {new_card.card_id}")
    print(f"Card name: {new_card.card_name}")
    print(f"Temp policy file: {temp_policy_path}")
    print(f"RAG raw reference: {reference_raw_path}")
    print()

    print("=== Step 2: Full Recommendation Flow ===")
    print(f"User message: {SPEND_SCENARIO_MESSAGE}")
    print(f"Parsed scenario: {result.parsed_scenario.model_dump()}")
    print(f"Best card: {result.best_card.card_name} ({result.best_card.card_id})")
    print(f"Net reward: {result.best_card.net_reward}")
    print(f"Reasoning: {result.best_card.reasoning}")
    print()

    print("=== Step 3: RAG References For Why It Is Best ===")
    print("Policy evidence from retriever:")
    for line in result.policy_evidence:
        print(f"- {line}")
    print()
    print("Chunk reference excerpt:")
    print(chunk_reference)


if __name__ == "__main__":
    t_nl_store_card_rank_and_explain()
