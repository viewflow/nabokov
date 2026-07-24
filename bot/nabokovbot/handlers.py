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

SKIP = "⏭ Пропустить"

START_TEXT = (
    "Привет! Я редактор на базе прозо-линтера nabokov.\n\n"
    "Пришли текст (до {max_words} слов) — уберу ИИ-штампы, верну ритм, "
    "или усилю как копирайтер. Для английских текстов покажу AI-likeness "
    "до и после (наш линтер английский; русские тексты правлю без скора).\n\n"
    "Первые {free} текста бесплатно, дальше {pack} текстов за {stars} ⭐ (/buy). "
    "Остаток — /balance."
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
                    text=f"{mark(mode == 'editor')}✍️ Редактор",
                    callback_data="mode:editor",
                ),
                InlineKeyboardButton(
                    text=f"{mark(mode == 'copywriter')}🚀 Копирайтер",
                    callback_data="mode:copywriter",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"{mark(creative == 0)}Креативность: норм",
                    callback_data="temp:0",
                ),
                InlineKeyboardButton(
                    text=f"{mark(creative == 1)}Повышенная",
                    callback_data="temp:1",
                ),
            ],
            [InlineKeyboardButton(text="▶️ Поехали", callback_data="run")],
        ]
    )


def _quota_line(message: Message) -> str:
    user = db.get_user(message.chat.id, message.chat.username)
    left = db.texts_left(user, message.chat.username)
    return "безлимит (админ)" if left is None else str(left)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    db.get_user(message.from_user.id, message.from_user.username)
    await message.answer(START_TEXT)


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    user = db.get_user(message.from_user.id, message.from_user.username)
    left = db.texts_left(user, message.from_user.username)
    if left is None:
        await message.answer("У тебя безлимит (админ).")
    else:
        await message.answer(
            f"Осталось текстов: {left}.\nПакет {config.PACK_TEXTS} текстов "
            f"за {config.PACK_STARS} ⭐ — /buy"
        )


@router.message(Command("buy"))
async def cmd_buy(message: Message) -> None:
    await message.answer_invoice(
        title=f"{config.PACK_TEXTS} текстов",
        description=(
            f"Пакет на {config.PACK_TEXTS} обработок текста "
            f"ботом @nabokov_editor_bot"
        ),
        payload="pack13",
        currency="XTR",
        prices=[LabeledPrice(label=f"{config.PACK_TEXTS} текстов", amount=config.PACK_STARS)],
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
    await message.answer(f"Спасибо! Добавил {config.PACK_TEXTS} текстов. Осталось: {left}.")


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
        await message.answer("Я ещё работаю над предыдущим текстом — секунду.")
        return

    words = len(text.split())
    if words > config.MAX_WORDS:
        await message.answer(
            f"Текст длинноват: {words} слов, лимит {config.MAX_WORDS}. "
            "Сократи или пришли частями."
        )
        return
    if words < 5:
        await message.answer("Пришли текст подлиннее — хотя бы несколько предложений.")
        return

    user = db.get_user(tg_id, message.from_user.username)
    left = db.texts_left(user, message.from_user.username)
    if left is not None and left <= 0:
        await cmd_buy(message)
        return

    db.set_pending(tg_id, text)
    lang_note = "" if linting.is_english(text) else "\n(русский текст — правка без скора)"
    await message.answer(
        f"Текст принят: {words} слов. Осталось текстов: {_quota_line(message)}.{lang_note}\n"
        "Что делаем?",
        reply_markup=_settings_keyboard("editor", 0),
    )


@router.callback_query(F.data.startswith("mode:"))
async def cb_mode(query: CallbackQuery) -> None:
    mode = query.data.split(":", 1)[1]
    db.update_pending(query.from_user.id, mode=mode)
    pending = db.get_pending(query.from_user.id)
    if pending:
        await query.message.edit_reply_markup(
            reply_markup=_settings_keyboard(pending["mode"], pending["creative"])
        )
    await query.answer()


@router.callback_query(F.data.startswith("temp:"))
async def cb_temp(query: CallbackQuery) -> None:
    creative = int(query.data.split(":", 1)[1])
    db.update_pending(query.from_user.id, creative=creative)
    pending = db.get_pending(query.from_user.id)
    if pending:
        await query.message.edit_reply_markup(
            reply_markup=_settings_keyboard(pending["mode"], pending["creative"])
        )
    await query.answer()


@router.callback_query(F.data.startswith("ans:"))
async def cb_answer(query: CallbackQuery) -> None:
    tg_id = query.from_user.id
    pending_q = _questions.pop(tg_id, None)
    if pending_q is None:
        await query.answer("Вопрос уже неактуален")
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
            f"❓ {question}\n(кнопкой или просто ответь сообщением)",
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
        await query.answer("Пришли текст заново", show_alert=True)
        return
    if tg_id in _running:
        await query.answer("Уже работаю")
        return

    user = db.get_user(tg_id, query.from_user.username)
    left = db.texts_left(user, query.from_user.username)
    if left is not None and left <= 0:
        await query.answer("Тексты закончились — /buy", show_alert=True)
        return

    await query.answer()
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    text, mode, creative = pending["text"], pending["mode"], bool(pending["creative"])
    _running.add(tg_id)
    status = await bot.send_message(tg_id, "🖋 Работаю…")
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
            await status.edit_text("✅ Готово:")
        except TelegramBadRequest:
            pass
        await _send_result(status, result)
        summary = []
        if before and after and before["score"] is not None and after["score"] is not None:
            summary.append(f"AI-likeness: {before['score']} → {after['score']}")
            summary.append(f"находок линтера: {before['findings_count']} → {after['findings_count']}")
        user = db.get_user(tg_id, query.from_user.username)
        left = db.texts_left(user, query.from_user.username)
        summary.append("осталось: безлимит" if left is None else f"осталось текстов: {left}")
        await bot.send_message(tg_id, "📊 " + " · ".join(summary))
    except Exception:
        logger.exception("job failed for %s", tg_id)
        await bot.send_message(
            tg_id, "Что-то сломалось, текст не списан. Попробуй ещё раз чуть позже."
        )
    finally:
        _running.discard(tg_id)
        _questions.pop(tg_id, None)
