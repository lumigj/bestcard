import asyncio

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bestcard.agents.orchestrator import RecommendationOrchestrator
from bestcard.config import settings
from bestcard.repository.policy_store import PolicyStore
from bestcard.schemas.requests import RecommendRequest

orchestrator = RecommendationOrchestrator(PolicyStore(settings.card_policy_file))


def _format_reply(payload) -> str:
    best = payload.best_card
    lines = [
        f"Best card: {best.card_name}",
        f"Net reward: ${best.net_reward:.2f} (cashback ${best.cashback:.2f}, fee ${best.fee:.2f})",
        f"Scenario: {payload.parsed_scenario.amount:.2f} / {payload.parsed_scenario.category}",
    ]
    if payload.policy_evidence:
        lines.append("Evidence:")
        lines.extend([f"- {item}" for item in payload.policy_evidence])
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Send your spend scenario, e.g. '今晚超市买200刀，哪张卡最好？'")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    try:
        result = orchestrator.recommend(RecommendRequest(message=text))
        await update.message.reply_text(_format_reply(result))
    except Exception as exc:
        await update.message.reply_text(f"Parse failed: {exc}")


def main() -> None:
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required.")

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    asyncio.run(asyncio.to_thread(main))
