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

# Создаём папку для аудиофайлов
if not os.path.exists('audio'):
    os.makedirs('audio')


class QuizState(StatesGroup):
    question = State()
    attempts = State()
    correct_count = State()


# Главное меню
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📖 Словарь"), KeyboardButton(text="📝 Викторина")],
        [KeyboardButton(text="📚 Грамматика")],
        [KeyboardButton(text="🌍 Для туристов"), KeyboardButton(text="🔊 Произношение")]
    ],
    resize_keyboard=True
)


async def create_tables():
    async with aiosqlite.connect("chinese_bot.db") as db:
        # Таблица слов
        await db.execute('''CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY,
            chinese TEXT UNIQUE,
            pinyin TEXT,
            translation TEXT,
            russian_transcription TEXT
        )''')

        # Таблица фраз для туристов
        await db.execute('''CREATE TABLE IF NOT EXISTS tourist_phrases (
            id INTEGER PRIMARY KEY,
            category TEXT,
            chinese TEXT UNIQUE,
            pinyin TEXT,
            translation TEXT
        )''')

        # Начальный словарь
        initial_words = [
            ("你好", "nǐ hǎo", "Привет", "нихао"),
            ("谢谢", "xièxiè", "Спасибо", "сесе"),
            ("再见", "zàijiàn", "До свидания", "цзайцзянь"),
            ("是", "shì", "Да", "ши"),
            ("不是", "bù shì", "Нет", "бу ши"),
            ("请", "qǐng", "Пожалуйста", "цин"),
            ("对不起", "duìbùqǐ", "Извините", "дуйбуци"),
            ("我", "wǒ", "Я", "во"),
            ("你", "nǐ", "Ты", "ни"),
            ("他", "tā", "Он", "та"),
            ("她", "tā", "Она", "та"),
            ("爱", "ài", "Любовь", "ай"),
            ("朋友", "péngyǒu", "Друг", "пэнъю"),
            ("老师", "lǎoshī", "Учитель", "лаоши"),
            ("学生", "xuéshēng", "Студент", "сюэшэн"),
            ("水", "shuǐ", "Вода", "шуй"),
            ("茶", "chá", "Чай", "ча"),
            ("饭", "fàn", "Еда", "фань"),
            ("家", "jiā", "Дом", "цзя"),
            ("书", "shū", "Книга", "шу"),
        ]
        await db.executemany(
            '''INSERT INTO words (chinese, pinyin, translation, russian_transcription)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(chinese) DO UPDATE SET
                   pinyin=excluded.pinyin,
                   translation=excluded.translation,
                   russian_transcription=excluded.russian_transcription''',
            initial_words
        )

        # Начальные фразы для туристов
        phrases = [
            ('Приветствия', '你好', 'nǐ hǎo', 'Здравствуйте'),
            ('Приветствия', '谢谢', 'xièxiè', 'Спасибо'),
            ('Приветствия', '再见', 'zàijiàn', 'До свидания'),
            ('Приветствия', '早上好', 'zǎoshang hǎo', 'Доброе утро'),
            ('Приветствия', '晚上好', 'wǎnshang hǎo', 'Добрый вечер'),
            ('Транспорт', '怎么去机场？', 'zěnme qù jīchǎng?', 'Как добраться до аэропорта?'),
            ('Транспорт', '地铁站在哪里？', 'dìtiě zhàn zài nǎlǐ?', 'Где станция метро?'),
            ('Транспорт', '请停在这里', 'qǐng tíng zài zhèlǐ', 'Остановитесь здесь, пожалуйста'),
            ('Транспорт', '到火车站多少钱？', 'dào huǒchē zhàn duōshǎo qián?', 'Сколько до вокзала?'),
            ('Транспорт', '我要买票', 'wǒ yào mǎi piào', 'Я хочу купить билет'),
        ]
        await db.executemany(
            '''INSERT INTO tourist_phrases (category, chinese, pinyin, translation)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(chinese) DO UPDATE SET
                   category=excluded.category,
                   pinyin=excluded.pinyin,
                   translation=excluded.translation''',
            phrases
        )

        # Удалим возможную ошибочную запись из старых версий БД
        await db.execute("DELETE FROM words WHERE chinese = 'книга'")
        # Удалим старые записи с английскими переводами (содержат латиницу)
        await db.execute("DELETE FROM words WHERE translation GLOB '*[A-Za-z]*'")
        await db.execute("DELETE FROM tourist_phrases WHERE translation GLOB '*[A-Za-z]*'")
        await db.commit()


@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
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
            response = "📖 Словарь:\n\n"
            for word in words:
                response += f"{word[0]} ({word[1]}) — {word[2]} [{word[3]}]\n"
            await message.answer(response[:4096])


@router.message(lambda message: message.text == "📚 Грамматика")
async def show_grammar(message: types.Message):
    grammar_rules = (
        "📚 Основные правила китайской грамматики:\n\n"
        "1️⃣ Порядок слов: подлежащее + сказуемое + дополнение.\n"
        "2️⃣ Глаголы не изменяются по времени — используются показатели времени.\n"
        "3️⃣ Вопросы образуются с помощью частицы 吗 (ma) или альтернативных конструкций.\n"
        "4️⃣ Частицы 了 (le) и 过 (guò) обозначают завершённость действия.\n\n"
        "Примеры предложений:\n"
        "🔹 我是学生。(Wǒ shì xuéshēng.) — Я студент.\n"
        "🔹 你喜欢喝茶吗？(Nǐ xǐhuān hē chá ma?) — Ты любишь пить чай?\n"
        "🔹 他昨天去了北京。(Tā zuótiān qùle Běijīng.) — Он вчера ездил в Пекин.\n"
    )
    await message.answer(grammar_rules)


# Обработчики для викторины
@router.message(lambda message: message.text == "📝 Викторина")
async def start_quiz(message: types.Message, state: FSMContext):
    await state.set_state(QuizState.question)
    await state.update_data(correct_count=0, attempts=0)
    quiz_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 В главное меню")]],
        resize_keyboard=True
    )
    await message.answer(
        "📝 Викторина началась! Выбирайте правильный перевод.\n"
        "Для выхода нажмите «🏠 В главное меню».",
        reply_markup=quiz_kb
    )
    await ask_question(message, state)


async def ask_question(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("chinese_bot.db") as db:
        async with db.execute("SELECT chinese, pinyin, translation FROM words ORDER BY RANDOM() LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if not row:
                await message.answer("В базе нет слов для викторины.", reply_markup=main_kb)
                await state.clear()
                return
            question_text = f"Как переводится: {row[0]} ({row[1]})?"
            correct_answer = row[2]
            async with db.execute(
                    "SELECT translation FROM words WHERE translation != ? ORDER BY RANDOM() LIMIT 3",
                    (correct_answer,)) as cursor:
                incorrect_answers = [r[0] for r in await cursor.fetchall()]

        options = [correct_answer] + incorrect_answers
        random.shuffle(options)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"quiz_{idx}")]
            for idx, opt in enumerate(options)
        ])
        await state.update_data(correct_answer=correct_answer, options=options)
        await message.answer(question_text, reply_markup=keyboard)


@router.callback_query(lambda call: call.data and call.data.startswith("quiz_"))
async def check_answer(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    options = data.get("options", [])

    try:
        idx = int(call.data[5:])
        user_answer = options[idx]
    except (ValueError, IndexError):
        await call.message.answer("Ошибка: не удалось распознать ответ.")
        return

    attempts = data.get("attempts", 0) + 1
    correct_count = data.get("correct_count", 0)

    if user_answer == correct_answer:
        correct_count += 1
        await call.message.answer(f"✅ Верно! Счёт: {correct_count}/{attempts}")
    else:
        await call.message.answer(
            f"❌ Неверно! Правильный ответ: {correct_answer}\nСчёт: {correct_count}/{attempts}"
        )

    await state.update_data(attempts=attempts, correct_count=correct_count)
    await ask_question(call.message, state)


# Обработчики для произношения
async def generate_audio(chinese_text: str, filename: str) -> str:
    filepath = f"audio/{filename}.mp3"
    tts = gTTS(text=chinese_text, lang='zh-CN')
    tts.save(filepath)
    return filepath


@router.message(lambda message: message.text == "🔊 Произношение")
async def pronunciation_practice(message: types.Message):
    async with aiosqlite.connect("chinese_bot.db") as db:
        async with db.execute("SELECT id, chinese, pinyin FROM words ORDER BY RANDOM() LIMIT 3") as cursor:
            words = await cursor.fetchall()

    if not words:
        await message.answer("В словаре пока нет слов для произношения.")
        return

    for word_id, chinese, pinyin in words:
        filename = f"word_{word_id}"
        filepath = await generate_audio(chinese, filename)
        with open(filepath, "rb") as audio_file:
            await message.answer_voice(
                types.BufferedInputFile(audio_file.read(), filename=f"{filename}.mp3"),
                caption=f"{chinese} ({pinyin})"
            )


# Обработчики для туристов
@router.message(lambda message: message.text == "🌍 Для туристов")
async def show_tourist_menu(message: types.Message):
    categories_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🙏 Приветствия"), KeyboardButton(text="🚇 Транспорт")],
            [KeyboardButton(text="💬 Основные фразы")],
            [KeyboardButton(text="🏠 В главное меню")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите категорию:", reply_markup=categories_kb)


@router.message(lambda message: message.text == "💬 Основные фразы")
async def show_main_phrases(message: types.Message):
    main_words = (
        "💬 Основные фразы:\n\n"
        "1. Здравствуйте! — 你好！(Nǐ hǎo!) — Нихао!\n"
        "2. Спасибо! — 谢谢！(Xièxiè!) — Сесе!\n"
        "3. Пожалуйста. — 请。(Qǐng.) — Цин.\n"
        "4. Извините. — 对不起。(Duìbùqǐ.) — Дуйбуци.\n"
        "5. Где находится туалет? — 洗手间在哪里？(Xǐshǒujiān zài nǎlǐ?) — Сишоуцзянь цзай нали?\n"
        "6. Сколько стоит? — 这个多少钱？(Zhège duōshǎo qián?) — Чжэгэ дошао цянь?\n"
        "7. Я не понимаю. — 我不懂。(Wǒ bù dǒng.) — Во бу дун.\n"
        "8. Помогите! — 救命！(Jiùmìng!) — Цзюмин!\n"
        "9. Где ближайшая станция метро? — 最近的地铁站在哪里？(Zuìjìn de dìtiě zhàn zài nǎlǐ?) — Цзуйцзинь дэ дитечжань цзай нали?\n"
        "10. Я хочу это купить. — 我想买这个。(Wǒ xiǎng mǎi zhège.) — Во сян май чжэгэ.\n"
        "11. Можно меню, пожалуйста? — 请给我菜单。(Qǐng gěi wǒ càidān.) — Цин гэй во цайдань.\n"
        "12. Как добраться до...? — 怎么去...? (Zěnme qù...?) — Цзэньмэ цюй...?\n"
        "13. У вас есть вегетарианские блюда? — 你们有素菜吗？(Nǐmen yǒu sùcài ma?) — Нимэнь ю суцай ма?\n"
        "14. У меня аллергия на... — 我对...过敏。(Wǒ duì... guòmǐn.) — Во дуй... гоминь.\n"
        "15. Я потерялся. — 我迷路了。(Wǒ mílù le.) — Во милу лэ."
    )
    await message.answer(main_words)


@router.message(lambda message: message.text == "🚇 Транспорт")
async def show_transport(message: types.Message):
    async with aiosqlite.connect("chinese_bot.db") as db:
        async with db.execute(
                "SELECT chinese, pinyin, translation FROM tourist_phrases WHERE category = 'Транспорт'") as cursor:
            phrases = await cursor.fetchall()

    if not phrases:
        await message.answer("Фразы о транспорте пока не добавлены.")
        return

    response = "🚇 Транспорт:\n\n"
    for idx, (chinese, pinyin, translation) in enumerate(phrases, 1):
        response += f"{idx}. {chinese} ({pinyin}) — {translation}\n"
    await message.answer(response)


@router.message(lambda message: message.text == "🙏 Приветствия")
async def show_greetings(message: types.Message):
    async with aiosqlite.connect("chinese_bot.db") as db:
        async with db.execute(
                "SELECT chinese, pinyin, translation FROM tourist_phrases WHERE category = 'Приветствия'") as cursor:
            phrases = await cursor.fetchall()

    if not phrases:
        await message.answer("Приветствия пока не добавлены.")
        return

    response = "🙏 Приветствия:\n\n"
    for idx, (chinese, pinyin, translation) in enumerate(phrases, 1):
        response += f"{idx}. {chinese} ({pinyin}) — {translation}\n"
    await message.answer(response)


@router.message(lambda message: message.text == "🏠 В главное меню")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_kb)


async def main():
    await create_tables()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
