"""Telegram handlers: text intake, settings keyboard, run, payments, ask_user."""

import asyncio
import html
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from . import config, db, deepseek, linting

logger = logging.getLogger(__name__)
router = Router()

# ask_user bridges: tg_id -> (future, options)
_questions: dict[int, tuple[asyncio.Future, list[str]]] = {}
_running: set[int] = set()

SKIP = "⏭ Skip"

START_TEXT = (
    "Hi! I'm an editor built on the nabokov prose linter.\n\n"
    "Send me a text (up to {max_words} words). I cut the AI slop and "
    "restore the rhythm, or punch it up in copywriter mode. English texts "
    "get the AI-likeness score before and after. The linter is "
    "English-only, so other languages get the edit without the score.\n\n"
    "First {free} texts are free, then {pack} texts for {stars} ⭐ (/buy). "
    "Check your balance with /balance."
).format(
    max_words=config.MAX_WORDS,
    free=config.FREE_TEXTS,
    pack=config.PACK_TEXTS,
    stars=config.PACK_STARS,
)


def _settings_keyboard(mode: str, creative: int) -> InlineKeyboardMarkup:
    def mark(flag: bool) -> str:
        return "✅ " if flag else ""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{mark(mode == 'editor')}✍️ Editor",
                    callback_data="mode:editor",
                ),
                InlineKeyboardButton(
                    text=f"{mark(mode == 'copywriter')}🚀 Copywriter",
                    callback_data="mode:copywriter",
                ),
            ],
            [
                # one toggle: shows the current value, tap to switch
                InlineKeyboardButton(
                    text=f"🎨 Creativity: {'raised' if creative else 'normal'}",
                    callback_data=f"temp:{0 if creative else 1}",
                ),
            ],
            [InlineKeyboardButton(text="▶️ Go", callback_data="run")],
        ]
    )


def _quota_line(message: Message) -> str:
    user = db.get_user(message.chat.id, message.chat.username)
    left = db.texts_left(user, message.chat.username)
    return "unlimited (admin)" if left is None else str(left)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    db.get_user(message.from_user.id, message.from_user.username)
    await message.answer(START_TEXT)


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    user = db.get_user(message.from_user.id, message.from_user.username)
    left = db.texts_left(user, message.from_user.username)
    if left is None:
        await message.answer("You have unlimited texts (admin).")
    else:
        await message.answer(
            f"Texts left: {left}.\nA pack of {config.PACK_TEXTS} texts "
            f"is {config.PACK_STARS} ⭐: /buy"
        )


@router.message(Command("buy"))
async def cmd_buy(message: Message) -> None:
    await message.answer_invoice(
        title=f"{config.PACK_TEXTS} texts",
        description=(
            f"A pack of {config.PACK_TEXTS} text edits "
            f"by @nabokov_editor_bot"
        ),
        payload="pack13",
        currency="XTR",
        prices=[LabeledPrice(label=f"{config.PACK_TEXTS} texts", amount=config.PACK_STARS)],
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def paid(message: Message) -> None:
    db.get_user(message.from_user.id, message.from_user.username)
    db.add_pack(message.from_user.id, message.successful_payment.telegram_payment_charge_id)
    user = db.get_user(message.from_user.id, message.from_user.username)
    left = db.texts_left(user, message.from_user.username)
    await message.answer(f"Thank you! Added {config.PACK_TEXTS} texts. Left: {left}.")


@router.message(F.text & ~F.text.startswith("/"))
async def incoming_text(message: Message) -> None:
    tg_id = message.from_user.id
    text = message.text.strip()

    # a pending clarifying question? free-text answers it
    pending_q = _questions.pop(tg_id, None)
    if pending_q is not None:
        future, _ = pending_q
        if not future.done():
            future.set_result(text)
        return

    if tg_id in _running:
        await message.answer("Still working on your previous text. One moment.")
        return

    words = len(text.split())
    if words > config.MAX_WORDS:
        await message.answer(
            f"That's {words} words; the limit is {config.MAX_WORDS}. "
            "Trim it or send it in parts."
        )
        return
    if words < 5:
        await message.answer("Send a longer text — at least a few sentences.")
        return

    user = db.get_user(tg_id, message.from_user.username)
    left = db.texts_left(user, message.from_user.username)
    if left is not None and left <= 0:
        await cmd_buy(message)
        return

    db.set_pending(tg_id, text)
    lang_note = "" if linting.is_english(text) else "\n(non-English text: edited without the score)"
    await message.answer(
        f"Got it: {words} words. Texts left: {_quota_line(message)}.{lang_note}\n"
        "What do we do?",
        reply_markup=_settings_keyboard("editor", 0),
    )


async def _refresh_settings(query: CallbackQuery) -> None:
    """Update the keyboard; tapping an already-selected option is a no-op
    (Telegram rejects an edit with identical markup)."""
    pending = db.get_pending(query.from_user.id)
    if pending:
        try:
            await query.message.edit_reply_markup(
                reply_markup=_settings_keyboard(pending["mode"], pending["creative"])
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.startswith("mode:"))
async def cb_mode(query: CallbackQuery) -> None:
    await query.answer()
    db.update_pending(query.from_user.id, mode=query.data.split(":", 1)[1])
    await _refresh_settings(query)


@router.callback_query(F.data.startswith("temp:"))
async def cb_temp(query: CallbackQuery) -> None:
    await query.answer()
    db.update_pending(query.from_user.id, creative=int(query.data.split(":", 1)[1]))
    await _refresh_settings(query)


@router.callback_query(F.data.startswith("ans:"))
async def cb_answer(query: CallbackQuery) -> None:
    tg_id = query.from_user.id
    pending_q = _questions.pop(tg_id, None)
    if pending_q is None:
        await query.answer("That question is no longer active")
        return
    future, options = pending_q
    idx = int(query.data.split(":", 1)[1])
    answer = SKIP if idx >= len(options) else options[idx]
    if not future.done():
        future.set_result(answer)
    try:
        await query.message.edit_text(f"{query.message.text}\n→ {answer}")
    except TelegramBadRequest:
        pass
    await query.answer()


def _make_ask(bot: Bot, tg_id: int) -> deepseek.AskFn:
    async def ask(question: str, options: list[str]) -> str:
        buttons = [
            [InlineKeyboardButton(text=o, callback_data=f"ans:{i}")]
            for i, o in enumerate(options)
        ]
        buttons.append(
            [InlineKeyboardButton(text=SKIP, callback_data=f"ans:{len(options)}")]
        )
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        _questions[tg_id] = (future, options)
        await bot.send_message(
            tg_id,
            f"❓ {question}\n(tap a button or just reply)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
        try:
            answer = await asyncio.wait_for(future, timeout=config.ASK_TIMEOUT_SECONDS)
        except TimeoutError:
            _questions.pop(tg_id, None)
            return "the user did not answer — do without that detail"
        if answer == SKIP:
            return "the user skipped the question — do without that detail"
        return answer

    return ask


async def _send_result(message: Message, text: str) -> None:
    """Markdown when the model wrote markdown; plain text as the fallback."""
    try:
        await message.answer(text, parse_mode="Markdown")
    except TelegramBadRequest:
        await message.answer(text)


@router.callback_query(F.data == "run")
async def cb_run(query: CallbackQuery, bot: Bot) -> None:
    tg_id = query.from_user.id
    pending = db.get_pending(tg_id)
    if pending is None:
        await query.answer("Send the text again", show_alert=True)
        return
    if tg_id in _running:
        await query.answer("Already on it")
        return

    user = db.get_user(tg_id, query.from_user.username)
    left = db.texts_left(user, query.from_user.username)
    if left is not None and left <= 0:
        await query.answer("You are out of texts: /buy", show_alert=True)
        return

    await query.answer()
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    text, mode, creative = pending["text"], pending["mode"], bool(pending["creative"])
    _running.add(tg_id)
    status = await bot.send_message(tg_id, "🖋 Working…")
    try:
        before = await asyncio.to_thread(linting.lint, text)
        result = await deepseek.rewrite(text, mode, creative, ask=_make_ask(bot, tg_id))
        after = await asyncio.to_thread(linting.lint, result)

        db.consume_text(tg_id, query.from_user.username)
        db.clear_pending(tg_id)
        db.log_job(
            tg_id,
            len(text.split()),
            mode,
            int(creative),
            before and before["score"],
            after and after["score"],
        )

        try:
            await status.edit_text("✅ Done:")
        except TelegramBadRequest:
            pass
        await _send_result(status, result)
        summary = []
        if before and after and before["score"] is not None and after["score"] is not None:
            summary.append(f"AI-likeness: {before['score']} → {after['score']}")
            summary.append(f"linter findings: {before['findings_count']} → {after['findings_count']}")
        user = db.get_user(tg_id, query.from_user.username)
        left = db.texts_left(user, query.from_user.username)
        summary.append("texts left: unlimited" if left is None else f"texts left: {left}")
        await bot.send_message(tg_id, "📊 " + " · ".join(summary))
    except Exception:
        logger.exception("job failed for %s", tg_id)
        await bot.send_message(
            tg_id, "Something broke and it did not cost you a text. Try again in a minute."
        )
    finally:
        _running.discard(tg_id)
        _questions.pop(tg_id, None)
