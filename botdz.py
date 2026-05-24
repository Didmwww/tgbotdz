import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import CommandStart, Command 
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)


TOKEN = "8553756391:AAE4UJoYWe4gP_XatK2F4HMajT-py3tV57Q" 
ADMIN_ID = 8145027393   
JAR_URL = "https://send.monobank.ua/jar/WuY7cBikB" 
ADMIN_USERNAME = "@ssermonss"   


QUEUE = []


PRICES = {
    "Реферат/Доповідь - 100 грн": 100,
    "Презентація - 150 грн": 150,
    "Лаба - 200 грн": 200
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


class OrderForm(StatesGroup):
    waiting_for_course = State()
    waiting_for_subject = State()
    waiting_for_task = State()

class PaymentConfirmation(StatesGroup):
    waiting_for_sender_name = State()

class AdminResponse(StatesGroup):
    waiting_for_id = State()
    waiting_for_content = State()


main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Реферат/Доповідь - 100 грн"), KeyboardButton(text="Презентація - 150 грн")],
        [KeyboardButton(text="Лаба - 200 грн"), KeyboardButton(text="Курсач - від 1000 грн")],
        [KeyboardButton(text="💬 Зв'язок з адміном")]
    ],
    resize_keyboard=True, input_field_placeholder="Меню"
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Скасувати та в меню")]],
    resize_keyboard=True
)


def add_to_queue(user_id):
    """Додає юзера в чергу, якщо його там немає"""
    if user_id not in QUEUE:
        QUEUE.append(user_id)
    return QUEUE.index(user_id) + 1

def remove_from_queue(user_id):
    """Видаляє юзера з черги"""
    if user_id in QUEUE:
        QUEUE.remove(user_id)

def get_queue_position(user_id):
    """Дізнатися позицію (якщо юзер є в черзі)"""
    if user_id in QUEUE:
        return QUEUE.index(user_id) + 1
    return 0



@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>Привіт! Я допоможу тобі з навчанням.</b>\n\n"
        "🕒 <b>Графік роботи:</b> 10:00 - 22:00\n"
        "☕ <b>Перерва:</b> 13:00 - 14:00\n"
        f"🏃 <b>Зараз у черзі людей: {len(QUEUE)}</b>\n\n"
        "Обери, що потрібно виконати:",
        reply_markup=main_kb, parse_mode="HTML"
    )

@router.message(F.text == "❌ Скасувати та в меню")
async def cancel_action(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Скасовано.", reply_markup=main_kb)

@router.message(F.text == "💬 Зв'язок з адміном")
async def contact_admin(message: types.Message):
    await message.answer(f"📞 З будь-яких питань: {ADMIN_USERNAME}")

@router.message(F.text == "Курсач - від 1000 грн")
async def coursework(message: types.Message):
    await message.answer(f"🎓 Курсові індивідуально: {ADMIN_USERNAME}", reply_markup=main_kb)



@router.message(F.text.in_(PRICES.keys()))
async def service_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(service=message.text)
    await message.answer("1️⃣ Вкажи свій курс (цифрою):", reply_markup=cancel_kb)
    await state.set_state(OrderForm.waiting_for_course)

@router.message(OrderForm.waiting_for_course)
async def course_step(message: types.Message, state: FSMContext):
    await state.update_data(course=message.text)
    await message.answer("2️⃣ Напиши назву предмету:", reply_markup=cancel_kb)
    await state.set_state(OrderForm.waiting_for_subject)

@router.message(OrderForm.waiting_for_subject)
async def subject_step(message: types.Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await message.answer(
        "3️⃣ <b>НАДІШЛИ ЗАВДАННЯ:</b>\n\n"
        "❗ <b>ТЕКСТ АБО ПОСИЛАННЯ НА ГУГЛ ДИСК</b>\n"
        "⚠️ <i>(ОБОВ'ЯЗКОВО ВІДКРИЙТЕ ДОСТУП!)</i>\n\n"
        "Також можна прикріпити <b>ФОТО, ФАЙЛ, АРХІВ</b>.\n\n"
        "Чекаю...",
        parse_mode="HTML", reply_markup=cancel_kb
    )
    await state.set_state(OrderForm.waiting_for_task)



@router.message(OrderForm.waiting_for_task)
async def task_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    service_name = data['service']
    price = PRICES[service_name]
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "Hidden"


    position = add_to_queue(user_id)

    await message.answer(
        f"⏳ <b>Завдання прийнято на модерацію!</b>\n"
        f"🔢 <b>Ваш номер у черзі: {position}</b>\n\n"
        "Адміністратор перевірить умову. Очікуйте.",
        reply_markup=main_kb, parse_mode="HTML"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Прийняти", callback_data=f"approve_{user_id}_{price}")],
        [InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject_{user_id}")]
    ])
    
    caption = message.caption if message.caption else message.text
    if not caption: caption = "(Без тексту)"

    admin_info = (
        f"🆕 <b>НОВА ЗАЯВКА (У черзі: {position}):</b>\n"
        f"👤 {username} (ID: {user_id})\n"
        f"💰 {service_name}\n"
        f"📚 {data['subject']} ({data['course']} курс)\n"
        f"📝 {caption}\n⬇️ <b>Вкладення:</b>"
    )

    try:
        await bot.send_message(ADMIN_ID, admin_info, reply_markup=keyboard, parse_mode="HTML")
        await message.forward(chat_id=ADMIN_ID)
    except Exception as e:
        await bot.send_message(ADMIN_ID, f"⚠️ Помилка пересилки: {e}")

    await state.clear()


@router.callback_query(F.data.startswith("reject_"))
async def admin_reject_task(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    
    remove_from_queue(user_id)
    
    await callback.message.edit_text(f"❌ <b>Відхилено.</b>\n{callback.message.html_text}", parse_mode="HTML")
    try: await bot.send_message(user_id, "😔 Вашу заявку відхилено.")
    except: pass

@router.callback_query(F.data.startswith("approve_"))
async def admin_approve_task(callback: CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    price = int(parts[2])
    
    pos = get_queue_position(user_id)
    
    await callback.message.edit_text(f"✅ <b>Чекаємо оплату.</b>\n{callback.message.html_text}", parse_mode="HTML")

    user_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Оплатити {price} грн", url=JAR_URL)],
        [InlineKeyboardButton(text="✅ Я оплатив", callback_data=f"startpay_{price}")]
    ])
    
    try:
        await bot.send_message(
            user_id,
            f"🥳 <b>Завдання схвалено!</b>\n"
            f"🔢 Ви <b>№{pos}</b> у черзі на виконання.\n"
            f"💰 До сплати: <b>{price} грн</b>\n\n"
            f"Натисніть кнопку оплати.",
            reply_markup=user_kb, parse_mode="HTML"
        )
    except: pass


@router.callback_query(F.data.startswith("startpay_"))
async def ask_sender_name(callback: CallbackQuery, state: FSMContext):
    price = callback.data.split("_")[1]
    await state.update_data(price=price)
    await callback.message.edit_text("✍️ <b>Вкажіть ПІБ платника:</b>", parse_mode="HTML")
    await state.set_state(PaymentConfirmation.waiting_for_sender_name)

@router.message(PaymentConfirmation.waiting_for_sender_name)
async def verify_payment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    price = data.get('price')
    sender = message.text
    user_id = message.from_user.id
    
    await message.answer("✅ <b>Дані надіслано.</b>", reply_markup=main_kb, parse_mode="HTML")

    admin_pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Гроші є", callback_data=f"payok_{user_id}_{price}")],
        [InlineKeyboardButton(text="⛔ Грошей немає", callback_data=f"payno_{user_id}")]
    ])

    await bot.send_message(
        ADMIN_ID, 
        f"💸 <b>ПЕРЕВІРКА ОПЛАТИ!</b>\n👤 {sender}\n💰 {price} грн\nID: {user_id}",
        reply_markup=admin_pay_kb, parse_mode="HTML"
    )
    await state.clear()

@router.callback_query(F.data.startswith("payno_"))
async def payment_rejected(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    remove_from_queue(uid)
    
    await callback.message.edit_text(f"⛔ <b>Відхилено (Нема оплати).</b>\n{callback.message.html_text}", parse_mode="HTML")
    try: await bot.send_message(uid, "⛔ Оплату не знайдено.")
    except: pass

@router.callback_query(F.data.startswith("payok_"))
async def payment_accepted(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    pos = get_queue_position(uid)
    
    await callback.message.edit_text(f"✅ <b>Оплачено. В роботі.</b>\n{callback.message.html_text}", parse_mode="HTML")
    try: 
        await bot.send_message(uid, f"✅ <b>Оплату зараховано!</b>\nВаш номер у черзі: <b>{pos}</b>. Ми працюємо.", parse_mode="HTML")
    except: pass

@router.message(Command("send"))
async def send_init(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🆔 Введіть ID студента:")
    await state.set_state(AdminResponse.waiting_for_id)

@router.message(AdminResponse.waiting_for_id)
async def send_id(message: types.Message, state: FSMContext):
    try:
        tid = int(message.text)
        await state.update_data(tid=tid)
        
        if tid in QUEUE:
            await message.answer(f"⚠️ Цей студент №{QUEUE.index(tid)+1} у черзі.\n📂 Кидайте файл/текст:")
        else:
            await message.answer("⚠️ Цього студента немає у списку черги (можливо вже видалений).\n📂 Кидайте файл все одно:")
            
        await state.set_state(AdminResponse.waiting_for_content)
    except: await message.answer("ID має бути числом!")

@router.message(AdminResponse.waiting_for_content)
async def send_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_id = data['tid']
    
    try:
        await message.copy_to(chat_id=target_id)
        await message.answer("✅ Надіслано студенту!")
        
        remove_from_queue(target_id)
        
    except Exception as e:
        await message.answer(f"Помилка: {e}")
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("БОТ ЗАПУЩЕНИЙ! ЧЕРГА АКТИВНА.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())