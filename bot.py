import asyncio
import html
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import BOT_TOKEN, PHOTO_ID, manager_id
from db import close_pool, create_ticket, get_ticket, init_pool, set_ticket_status

MANAGER_USER_ID = int(manager_id) if manager_id else None


if not BOT_TOKEN:
    raise ValueError("Токен не найден!")

btn_request = KeyboardButton(text="Оставить заявку")
btn_about = KeyboardButton(text="О компании")
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [btn_request, btn_about],
    ],
    resize_keyboard=True,
)

direction_btn = {
    "dir_sings": "Знаки",
    "dir_stales": "Стеллы",
    "dir_metal": "Металлоконструкции",
    "dir_brand": "Брендирование",
    "dir_services": "Услуги",
    "dir_product": "Производство",
    "dir_other": "Другое",
}

rows = [
    ["dir_sings", "dir_stales"],
    ["dir_metal", "dir_brand"],
    ["dir_services", "dir_product", "dir_other"],
]

direction_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text=direction_btn[key], callback_data=key)
            for key in row
        ]
        for row in rows
    ]
)

manager_btn = {
    "close": "Закрыть заявку",
    "reopen": "Открыть заявку",
}


class RequestForm(StatesGroup):
    name = State()
    org = State()
    city = State()
    direction = State()
    description = State()
    phone = State()


main_router = Router()
form_router = Router()


@form_router.message(CommandStart())
async def cmd_start(message: Message):
    name = message.from_user.username or "вас приветствует бот vizteh"
    if message.from_user.id == MANAGER_USER_ID:
        await message.answer(
            f"Здравствуйте, менеджер {name}",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await message.answer(
            f"Здравствуйте, {name}",
            reply_markup=main_kb,
        )


# Функция для загрузки своего фото для текста "О компании". ! Доступна только менеджеру
#
# @router.message(Command("photoid"))
# async def get_photo_id(message: Message):
#     if message.from_user.id != MANAGER_CHAT_ID:
#         await message.answer("Это функция администратора")
#         return
#     else:
#         if not message.photo:
#             await message.answer("Пришлите фото с подписью /photoid")
#             return
#         file_id = message.photo[-1].file_id
#         await message.answer(f"ID фото - {file_id}")


@form_router.message(F.text == "Оставить заявку")
async def handler_request(message: Message, state: FSMContext):
    if message.from_user.id == MANAGER_USER_ID:
        await message.answer("Это функция пользователя!")
        return
    await state.set_state(RequestForm.name)
    await message.answer("Как к вам обращаться?")


@form_router.message(RequestForm.name)
async def process_name(message: Message, state: FSMContext):
    if message.text is None:
        await message.answer("Пожалуйста, отправте текстом.")
        return
    if not message.text.strip():
        await message.answer("Введите имя.")
        return

    await state.update_data(name=message.text)
    await state.set_state(RequestForm.org)
    await message.answer("Укажите вашу организацию:")


@form_router.message(RequestForm.org)
async def process_org(message: Message, state: FSMContext):
    if message.text is None:
        await message.answer("Пожалуйста, отправте текстом.")
        return
    if not message.text.strip():
        await message.answer("Введите организацию.")
        return
    await state.update_data(org=message.text)
    await state.set_state(RequestForm.city)
    await message.answer("Из какого вы города?")


@form_router.message(RequestForm.city)
async def process_city(message: Message, state: FSMContext):
    if message.text is None:
        await message.answer("Пожалуйста, отправте текстом.")
        return
    if not message.text.strip():
        await message.answer("Введите город.")
        return
    await state.update_data(city=message.text)
    await state.set_state(RequestForm.direction)
    await message.answer("Выбирите направление:", reply_markup=direction_kb)


@form_router.callback_query(RequestForm.direction)
async def process_direction(callback: CallbackQuery, state: FSMContext):
    call_querty = callback.data

    direction = direction_btn.get(call_querty)
    if not direction:
        await callback.answer("Выберите направление из кнопок", show_alert=True)
        return
    await state.update_data(direction=direction)
    await state.set_state(RequestForm.description)
    await callback.message.answer(
        "Кратко опишите вашу задачу.\n"
        "Например: какие конструкции нужны, примерные размеры, где будет размещаться и т.п."
    )
    await callback.answer()


@form_router.message(RequestForm.description)
async def process_description(message: Message, state: FSMContext):
    if message.text is None:
        await message.answer("Пожалуйста, отправте текстом.")
        return
    if not message.text.strip():
        await message.answer("Введите описание задачи.")
        return
    await state.update_data(description=message.text)
    await state.set_state(RequestForm.phone)
    await message.answer("Оставьте контактный номер телефона.\n")


@main_router.message(F.text == "О компании")
async def handler_about_button(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == MANAGER_USER_ID:
        await message.answer("Это функция пользователя!")
        return
    phone = 74953632042
    await message.answer_photo(
        photo=PHOTO_ID,
        caption=(
            "🏭 «Визуальные технологии» — проектируем и производим системы визуального информирования и ориентирования для городских и промышленно-технологических пространств.\n✅ Работа “под ключ” — от идеи и проектирования до монтажа и сервиса.\n"
            "🛠 Собственное производство — контроль сроков и качества, изготовление тиражей и нестандартных конструкций.\n"
            "📌 Надёжность — 10 лет на рынке, более 800 контрактов; среди заказчиков: ПАО «Газпром», ОАО «РЖД», Московский метрополитен.\n\n"
            f"Остались вопросы? Свяжитесь с Нами!\n📞 +{phone}\n\n"
            "Наш сайт: <a href='https://vizteh.ru/'>vizteh.ru</a>"
        ),
        parse_mode="HTML",
    )


def format_request_text(data):
    id = data.get("ticket_id") or data.get("id")
    name = data.get("name")
    username = data.get("username")
    if username:
        username = "@" + username
    else:
        username = "отсутствует"
    org = data.get("org")
    city = data.get("city")
    direction = data.get("direction")
    description = data.get("description")
    phone = data.get("phone")
    return (
        f"Новая заявка: №{id}\n\n"
        f"Имя: {name}\n"
        f"Имя пользователя Telegram: {username}\n"
        f"Организация: {org}\n"
        f"Город: {city}\n"
        f"Направление: {direction}\n"
        f"Описание: {description}\n"
        f"Телефон: {phone}"
    )


@form_router.message(RequestForm.phone)
async def process_phone(message: Message, state: FSMContext, bot: Bot):
    if message.text is None:
        await message.answer("Пожалуйста, отправте текстом.")
        return
    if not message.text.strip():
        await message.answer("Введите телефон.")
        return
    digits = "".join(ch for ch in message.text if ch.isdigit())
    if len(digits) < 10:
        await message.answer("Введите номер правильно, пример: +74953632042")
        return
    if digits.startswith("8") and len(digits) == 11:
        phone_res = "+7" + digits[1:]
    elif digits.startswith("7") and len(digits) == 11:
        phone_res = "+" + digits
    elif len(digits) == 10:
        phone_res = "+7" + digits
    else:
        phone_res = "+" + digits

    await state.update_data(phone=phone_res)
    data = await state.get_data()
    data["user_id"] = message.from_user.id
    data["username"] = message.from_user.username
    data["manager_id"] = MANAGER_USER_ID

    manager_phone = 74953632042

    await state.clear()
    ticket_id = await create_ticket(data)
    data["ticket_id"] = ticket_id
    request_text = "🟢 " + format_request_text(data)

    if MANAGER_USER_ID:
        await bot.send_message(
            chat_id=MANAGER_USER_ID,
            text=request_text,
            reply_markup=manager_kb(ticket_id, "open"),
        )

    await message.answer(
        "Спасибо! Ваша заявка отправленна менеджеру.\n"
        "Мы свяжемся с вами в ближайшее время.\n\n"
        f"Остались вопросы? Свяжитесь с Нами!\n📞 +{manager_phone}\n\n"
    )


def manager_kb(ticket_id: int, status: str):
    kb = InlineKeyboardBuilder()
    if status == "open":
        action = "close"
    else:
        action = "reopen"
    kb.button(
        text=manager_btn[action], callback_data=f"question_status:{action}:{ticket_id}"
    )
    return kb.as_markup()


@form_router.callback_query(F.data.startswith("question_status:"))
async def on_status_action(callback: CallbackQuery):
    if callback.from_user.id != MANAGER_USER_ID:
        await callback.answer("Это функция админитсратора!", show_alert=True)
        return
    _, status, ticket_id = callback.data.split(":")
    ticket_id = int(ticket_id)

    ticket = await get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    base_text = format_request_text(ticket)
    safe_text = html.escape(base_text)
    if status == "close":
        close_at = await set_ticket_status(ticket_id, "closed")
        who = callback.from_user.full_name
        time_str = close_at.strftime("%d.%m.%Y %H:%M")
        new_text = "🔴 " + f"<s>{safe_text}</s>" + f"\n\nЗакрыто: {who} {time_str}"
        kb_status = "closed"
    elif status == "reopen":
        await set_ticket_status(ticket_id, "open")
        new_text = "🟢 " + safe_text
        kb_status = "open"

    await callback.message.edit_text(
        new_text, reply_markup=manager_kb(ticket_id, kb_status), parse_mode="HTML"
    )
    await callback.answer()


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(main_router)
    dp.include_router(form_router)
    await init_pool()
    try:
        await dp.start_polling(bot)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
