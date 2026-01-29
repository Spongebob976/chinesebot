import logging
import asyncio
import aiosqlite
import os
from gtts import gTTS
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import random

API_TOKEN = "7897594146:AAEvSr0JN96-2ijYLkUTfTVX7a1W2APNtIE"

# Инициализация бота и диспетчера
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Создаем папку для аудиофайлов
if not os.path.exists('audio'):
    os.makedirs('audio')


class QuizState(StatesGroup):
    question = State()
    attempts = State()
    correct_count = State()


class GrammarPracticeState(StatesGroup):
    answer = State()


# Главное меню
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📖 Словарь"), KeyboardButton(text="📝 Викторина")],
        [KeyboardButton(text="📚 Грамматика"), ],
        [KeyboardButton(text="🌍 Для туристов"), KeyboardButton(text="🔊 Произношение")]
    ],
    resize_keyboard=True
)


async def create_tables():
    async with aiosqlite.connect("chinese_bot.db") as db:
        # Таблица слов
        await db.execute('''CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY,
            chinese TEXT,
            pinyin TEXT,
            translation TEXT,
            russian_transcription TEXT
        )''')

        # Таблица фраз для туристов
        await db.execute('''CREATE TABLE IF NOT EXISTS tourist_phrases (
            id INTEGER PRIMARY KEY,
            category TEXT,
            chinese TEXT,
            pinyin TEXT,
            translation TEXT
        )''')

        # Добавляем тестовые данные
        initial_words = [
            ("你好", "nǐ hǎo", "Привет", "ни хао"),
            ("谢谢", "xiè xiè", "Спасибо", "се се"),
            ("再见", "zài jiàn", "До свидания", "цзай цзянь")
        ]
        await db.executemany(
            'INSERT OR IGNORE INTO words (chinese, pinyin, translation, russian_transcription) VALUES (?, ?, ?, ?)',
            initial_words
        )

        phrases = [
            ('Приветствия', '你好', 'nǐ hǎo', 'Здравствуйте'),
            ('Приветствия', '谢谢', 'xiè xiè', 'Спасибо'),
            ('Транспорт', '地铁站在哪里？', 'dìtiě zhàn zài nǎlǐ?', 'Где станция метро?'),
        ]
        await db.executemany(
            'INSERT OR IGNORE INTO tourist_phrases (category, chinese, pinyin, translation) VALUES (?, ?, ?, ?)',
            phrases
        )
        await db.commit()


@router.message(Command("start"))
async def start_command(message: types.Message):
    await create_tables()
    await message.answer(
        "🇨🇳 你好! Добро пожаловать в бота для изучения китайского!\nВыберите действие:",
        reply_markup=main_kb
    )


# Обработчики для словаря
@router.message(lambda message: message.text == "📖 Словарь")
async def show_dictionary(message: types.Message):
    async with aiosqlite.connect("chinese_bot.db") as db:
        async with db.execute("SELECT chinese, pinyin, translation, russian_transcription FROM words") as cursor:
            words = await cursor.fetchall()
            if not words:
                await message.answer("Словарь пока пуст.")
                return
            response = "Словарь:\n"
            for word in words:
                response += f"{word[0]} ({word[1]}) - {word[2]} [{word[3]}]\n"
            await message.answer(response[:4096])


@router.message(lambda message: message.text == "📚 Грамматика")
async def show_grammar(message: types.Message):
    grammar_rules = (
        "Основные правила китайской грамматики:\n"
        "1️⃣ В китайском языке порядок слов - подлежащее + сказуемое + дополнение.\n"
        "2️⃣ Нет изменений глаголов по времени, используются указатели времени.\n"
        "3️⃣ Вопросы формируются с помощью 吗 (ma) или альтернативных вопросов.\n"
        "4️⃣ Частицы 了 (le) и 过 (guò) обозначают завершенность действия.\n\n"
        "Примеры предложений:\n"
        "🔹 我是学生。(Wǒ shì xuéshēng.) - Я студент.\n"
        "🔹 你喜欢喝茶吗？(Nǐ xǐhuān hē chá ma?) - Ты любишь пить чай?\n"
        "🔹 他昨天去了北京。(Tā zuótiān qùle Běijīng.) - Он вчера ездил в Пекин.\n"
    )
    await message.answer(grammar_rules)

# Обработчики для викторины
@router.message(lambda message: message.text == "📝 Викторина")
async def start_quiz(message: types.Message, state: FSMContext):
    await state.set_state(QuizState.question)
    await state.update_data(correct_count=0, attempts=0)
    await ask_question(message, state)


async def ask_question(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("chinese_bot.db") as db:
        async with db.execute("SELECT chinese, pinyin, translation FROM words ORDER BY RANDOM() LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if not row:
                await message.answer("В базе нет слов для викторины.")
                return
            question_text = f"Как переводится: {row[0]} ({row[1]})?"
            correct_answer = row[2]
            async with db.execute("SELECT translation FROM words WHERE translation != ? ORDER BY RANDOM() LIMIT 3",
                                  (correct_answer,)) as cursor:
                incorrect_answers = [r[0] for r in await cursor.fetchall()]
            options = [correct_answer] + incorrect_answers
            random.shuffle(options)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=opt, callback_data=f"quiz_{opt}")] for opt in options
            ])
            await state.update_data(correct_answer=correct_answer)
            await message.answer(question_text, reply_markup=keyboard)


@router.callback_query(lambda call: call.data.startswith("quiz_"))
async def check_answer(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    user_answer = call.data[5:]

    if user_answer == correct_answer:
        await call.message.answer("✅ Верно!")
    else:
        await call.message.answer(f"❌ Неверно! Правильный ответ: {correct_answer}")

    await ask_question(call.message, state)


# Обработчики для произношения
async def generate_audio(text: str, filename: str):
    tts = gTTS(text=text, lang='zh-cn')
    tts.save(f"audio/{filename}.mp3")


@router.message(lambda message: message.text == "🔊 Произношение")
async def pronunciation_practice(message: types.Message):
    async with aiosqlite.connect("chinese_bot.db") as db:
        async with db.execute("SELECT chinese, pinyin FROM words ORDER BY RANDOM() LIMIT 3") as cursor:
            words = await cursor.fetchall()
            for chinese, pinyin in words:
                await generate_audio(pinyin, chinese)
                with open(f"audio/{chinese}.mp3", "rb") as audio_file:
                    await message.answer_voice(
                        types.BufferedInputFile(audio_file.read(), filename=f"{chinese}.mp3"),
                        caption=f"{chinese} ({pinyin})"
                    )


# Обработчики для туристов
@router.message(lambda message: message.text == "🌍 Для туристов")
async def show_tourist_menu(message: types.Message):
    categories_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🙏 Приветствия"), KeyboardButton(text="🚇 Транспорт"), KeyboardButton(text="Основные фразы")],
            [KeyboardButton(text="🏠 В главное меню")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите категорию:", reply_markup=categories_kb)


@router.message(lambda message: message.text == "Основные фразы")
async def show_grammar(message: types.Message):
    main_words = (
        "1. Здравствуйте! - 你好！(Nǐ hǎo!) - Ни хао!\n"
        "2. Спасибо! - 谢谢！(Xièxiè!) - Сиэсиэ!\n"
        "3. Пожалуйста. - 请。(Qǐng.) - Цинь.\n"
        "4. Извините. - 对不起。(Duìbùqǐ.) - Дуйбуци.\n"
        "5. Где находится туалет? - 洗手间在哪里？(Xǐshǒujiān zài nǎlǐ?) - Сишоудзян цзай налий?\n"
        "6. Сколько стоит? - 这个多少钱？(Zhège duōshǎo qián?) - Чэго дуошао цянь?\n"
        "7. Я не понимаю. - 我不懂。(Wǒ bù dǒng.) - Во бу дун.\n"
        "8. Помогите! - 救命！(Jiùmìng!) - Цзюмин!\n"
        "9. Где ближайшая станция метро? - 最近的地铁站在哪里？(Zuìjìn de dìtiě zhàn zài nǎlǐ?) - Цзуйцзинь дэ дитиэ чжан цзай налий?\n"
        "10. Я хочу это купить. - 我想买这个。(Wǒ xiǎng mǎi zhège.) - Во сянь май чэго.\n"
        "11. Можно меню, пожалуйста? - 请给我菜单。(Qǐng gěi wǒ càidān.) - Цинь гэй во цайдан.\n"
        "12. Как добраться до...? - 怎么去...? (Zěnme qù...?) - Цзэньме цюй...?\n"
        "13. У вас есть вегетарианские блюда? - 你们有素菜吗？(Nǐmen yǒu sùcài ma?) - Нимен ёу суцай ма?\n"
        "14. Я аллергик на... - 我对...过敏。(Wǒ duì... guòmǐn.) - Во дуй... гуомин.\n"
        "15. Я потерялся. - 我迷路了。(Wǒ mílù le.) - Во милу лэ."
    )
    await message.answer(main_words)


# В раздел создания таблиц добавим дополнительные фразы
async def create_tables():
    async with aiosqlite.connect("chinese_bot.db") as db:
        # ... предыдущий код ...

        transport_phrases = [
            ('Транспорт', '怎么去机场？', 'zěnme qù jīchǎng?', 'Как добраться до аэропорта?'),
            ('Транспорт', '地铁站在哪里？', 'dìtiě zhàn zài nǎlǐ?', 'Где станция метро?'),
            ('Транспорт', '请停在这里', 'qǐng tíng zài zhèlǐ', 'Остановитесь здесь, пожалуйста'),
            ('Транспорт', '到火车站多少钱？', 'dào huǒchē zhàn duōshǎo qián?', 'Сколько до вокзала?'),
            ('Транспорт', '我要买票', 'wǒ yào mǎi piào', 'Я хочу купить билет')
        ]
        await db.executemany(
            'INSERT OR IGNORE INTO tourist_phrases (category, chinese, pinyin, translation) VALUES (?, ?, ?, ?)',
            transport_phrases
        )
        await db.commit()


# Добавим новый обработчик для транспорта
@router.message(lambda message: message.text == "🚇 Транспорт")
async def show_transport(message: types.Message):
    async with aiosqlite.connect("chinese_bot.db") as db:
        async with db.execute(
                "SELECT chinese, pinyin, translation FROM tourist_phrases WHERE category = 'Транспорт'") as cursor:
            phrases = await cursor.fetchall()
            response = "🚇 Транспорт:\n\n"
            for idx, (chinese, pinyin, translation) in enumerate(phrases, 1):
                response += f"{idx}. {chinese} ({pinyin}) - {translation}\n"
            await message.answer(response)


@router.message(lambda message: message.text == "🙏 Приветствия")
async def show_greetings(message: types.Message):
    async with aiosqlite.connect("chinese_bot.db") as db:
        async with db.execute(
                "SELECT chinese, pinyin, translation FROM tourist_phrases WHERE category = 'Приветствия'") as cursor:
            phrases = await cursor.fetchall()
            response = "🙏 Приветствия:\n\n"
            for idx, (chinese, pinyin, translation) in enumerate(phrases, 1):
                response += f"{idx}. {chinese} ({pinyin}) - {translation}\n"
            await message.answer(response)


@router.message(lambda message: message.text == "🏠 В главное меню")
async def back_to_main(message: types.Message):
    await message.answer("Главное меню:", reply_markup=main_kb)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())