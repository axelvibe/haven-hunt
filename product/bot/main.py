"""HavenHunt Telegram bot — main entrypoint.

Run from the project root:  uv run python -m product.bot.main
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from product.bot.handlers import router
from product.shared.config import settings

log = logging.getLogger("havenhunt.bot")


async def main() -> None:
    if not settings.telegram_token:
        log.error("TELEGRAM_BOT_TOKEN is not set. Add it to .env (from @BotFather).")
        return

    bot = Bot(
        token=settings.telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    me = await bot.get_me()
    log.info("Connected as @%s (%s)", me.username, me.full_name)

    dp = Dispatcher()
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
