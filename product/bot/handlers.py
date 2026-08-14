"""HavenHunt Telegram bot — command and message handlers.

Conversation design (from the Designer's spec):
  - /start welcomes and offers one-tap search shortcuts
  - Free-text messages are parsed for intent, searched semantically, and answered
    in a warm, expert voice with photo cards for the top matches
  - Quick-filter buttons cover the most common jobs-to-be-done
"""
from __future__ import annotations

import asyncio
import html
import logging
import time
from functools import wraps

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from product.listings.models import Listing
from product.listings.provider import build_provider
from product.listings.search import Filters, SearchEngine
from product.shared.config import settings

log = logging.getLogger("havenhunt.bot.handlers")

router = Router()

_search = SearchEngine(provider=build_provider())

# ---- lightweight per-user cooldown (prevents API cost explosions) ----
_last_call: dict[int, float] = {}
_COOLDOWN = 2.0


def cooldown(seconds: float = _COOLDOWN):
    def deco(fn):
        @wraps(fn)
        async def wrapper(message: Message, *a, **kw):
            now = time.time()
            uid = message.from_user.id if message.from_user else 0
            if now - _last_call.get(uid, 0.0) < seconds:
                return None
            _last_call[uid] = now
            return await fn(message, *a, **kw)

        return wrapper

    return deco


# ---- keyboards --------------------------------------------------------
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔑 Find Rentals", callback_data="quick:rent"),
                InlineKeyboardButton(text="🏡 Homes For Sale", callback_data="quick:sale"),
            ],
            [
                InlineKeyboardButton(text="🐾 Pet-Friendly", callback_data="quick:pets"),
                InlineKeyboardButton(text="🧭 Help", callback_data="help"),
            ],
        ]
    )


def detail_row(listing: Listing) -> list[InlineKeyboardButton]:
    buttons: list[InlineKeyboardButton] = []
    if listing.listing_type == "rent":
        buttons.append(InlineKeyboardButton(text="🔑 Similar rentals", callback_data=f"like:rent:{listing.neighborhood}"))
    else:
        buttons.append(InlineKeyboardButton(text="🏡 Similar homes", callback_data=f"like:sale:{listing.neighborhood}"))
    if listing.external_url:
        buttons.append(InlineKeyboardButton(text="🔗 Listing link", url=listing.external_url))
    return buttons


# ---- helpers ----------------------------------------------------------
def _card_caption(listing: Listing) -> str:
    extra = ""
    if listing.source == "demo":
        extra = "\n<i>demo listing</i>"
    elif listing.source == "simplyrets":
        extra = "\n<i>live MLS listing</i>"
    return html.escape(listing.to_text()) + extra


async def _send_listing(message: Message, listing: Listing) -> None:
    cap = _card_caption(listing)
    try:
        if listing.image_url:
            await message.answer_photo(
                photo=listing.image_url,
                caption=cap,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[detail_row(listing)]),
            )
            return
    except (TelegramBadRequest, Exception):  # noqa: BLE001
        pass
    await message.answer(cap)


async def _run_search(message: Message, query: str, limit: int = 4) -> None:
    if not query.strip():
        await message.answer(
            "Try something like:\n"
            "• “2-bed rental under $2,500 in Lakeview”\n"
            "• “pet-friendly condos for sale near Wrigleyville”\n"
            "• “1-bedroom under $1,800”"
        )
        return
    typing = asyncio.create_task(message.answer_chat_action("typing"))
    result = await asyncio.to_thread(_search.answer, query, 5)
    await typing
    await message.answer(html.escape(result["answer"]), disable_web_page_preview=True)
    for listing in result["listings"][:limit]:
        await _send_listing(message, listing)
    if result["count"] > limit:
        await message.answer(
            f"Showing the top {limit} of {result['count']} matches — refine your "
            "query to narrow it down. Happy hunting! 🏠"
        )


async def _run_quick(message_or_cb: Message | CallbackQuery, kind: str) -> None:
    query_map = {
        "rent": "best rentals",
        "sale": "homes for sale",
        "pets": "pet friendly rentals",
    }
    query = query_map.get(kind, "best rentals")
    if isinstance(message_or_cb, CallbackQuery):
        await message_or_cb.answer()
        await _run_search(message_or_cb.message, query)
    else:
        await _run_search(message_or_cb, query)


# ---- commands ---------------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer_chat_action("typing")
    site = f" and explore the full story at <a href='{settings.site_url}'>havenhunt.site</a>" if settings.site_url else ""
    await message.answer(
        f"👋 <b>Welcome to HavenHunt!</b>\n\n"
        f"I'm your AI property scout for Chicago — I hunt down rentals and homes "
        f"for sale from listings across the city, using natural language.\n\n"
        f"Try me: “Find a 2-bed pet-friendly rental under $2,500 near the lake.”\n\n"
        f"Choose a shortcut below or just chat with me naturally.{site}",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
@router.callback_query(F.data == "help")
async def cmd_help(event: Message | CallbackQuery) -> None:
    text = (
        "🧭 <b>HavenHunt help</b>\n\n"
        "I can search Chicago listings for rent and sale. Ask me in plain English:\n\n"
        "• “1-bedroom rental under $1,900”\n"
        "• “3-bed house for sale in Lincoln Park”\n"
        "• “pet-friendly apartments near Wrigley”\n"
        "• “condos with parking under $500k”\n\n"
        "Commands:\n"
        "/start — main menu\n"
        "/search &lt;query&gt; — run a search\n"
        "/help — this message\n"
        "/web — open the website"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, reply_markup=main_menu())
    else:
        await event.answer(text, reply_markup=main_menu())


@router.message(Command("web"))
async def cmd_web(message: Message) -> None:
    url = settings.site_url or "https://github.com"
    await message.answer(
        f"🌐 Meet the <b>HavenHunt</b> organisation and try the web chat:\n{url}"
    )


@router.message(Command("search"))
@cooldown()
async def cmd_search(message: Message) -> None:
    query = (message.text or "").removeprefix("/search").strip()
    if not query:
        await message.answer(
            "Usage: /search <query>\nExample: /search 2-bed rental under $2,200"
        )
        return
    await _run_search(message, query)


@router.message(F.text)
@cooldown()
async def on_text(message: Message) -> None:
    await _run_search(message, message.text or "")


@router.callback_query(F.data.startswith("quick:"))
async def cb_quick(cb: CallbackQuery) -> None:
    await _run_quick(cb, cb.data.split(":", 1)[1])


@router.callback_query(F.data.startswith("like:"))
async def cb_like(cb: CallbackQuery) -> None:
    _, ltype, hood = cb.data.split(":", 2)
    await _run_search(
        cb.message,
        f"{'rental' if ltype == 'rent' else 'home for sale'} in {hood}",
        limit=3,
    )
