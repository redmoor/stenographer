import logging
import sqlite3
import tempfile
import asyncio
from functools import wraps

import ffmpeg
from telebot import types, asyncio_filters
from telebot.async_telebot import AsyncTeleBot
from telebot.states import State, StatesGroup

logger = logging.getLogger(__name__)

admin_commands = [
        types.BotCommand("auth", "Authorize a new user")
    ]

async def init(bot: AsyncTeleBot, admin_chat_id: int, connection: sqlite3.Connection, queue: asyncio.Queue) -> AsyncTeleBot:
    class States(StatesGroup):
        auth = State()

    @bot.message_handler(commands="start")
    async def _(message: types.Message):
        if message.chat.id == admin_chat_id:
            await bot.send_message(message.chat.id, "Welcome to the transcriber bot 🎈\n\nYou are an admin. \nTo start using the bot you have to authorize yourself first. \nRun /auth command and forward your own message to this chat or send your User ID.")
            return
        await bot.send_message(message.chat.id, "Welcome to the transcriber bot 🎈\n\nTo use the bot you need to be authorized. Plesase, contact the bot admin.")

    @bot.message_handler(commands="auth")
    async def _(message: types.Message):
        if message.chat.id != admin_chat_id:
            await bot.send_message(message.chat.id, "You have to be an admin to authorize a new user")
            return
        assert message.from_user is not None
        await bot.set_state(message.from_user.id, States.auth, message.chat.id)
        await bot.send_message(message.chat.id, "Forward message from the user or type User ID")

    @bot.message_handler(state=States.auth, content_types=['text', 'voice', 'video_note', 'photo'])
    async def _(message: types.Message):
        user_id = None

        if message.forward_from:
            user_id = message.forward_from.id

        elif message.forward_sender_name:
            await bot.send_message(message.chat.id, f"User {message.forward_sender_name} has 'Forward messages' privacy turned on. Can't retrieve an ID myself. Try sending User ID as a number")

        elif message.text and message.text.isdigit():
            user_id = int(message.text)

        else:
            await bot.send_message(message.chat.id, "Couldn't find a User ID. Try forwarding or sending the ID as a number.")

        if user_id is not None:
            cursor = connection.cursor()
            try:
                cursor.execute("INSERT INTO authorized_users (user_id) VALUES(?);", [user_id])
                connection.commit()
                await bot.send_message(message.chat.id, "User was successfully authorized")
                await bot.send_message(user_id, "You are authorized now.")
            except sqlite3.Error:
                await bot.send_message(message.chat.id, "User is already authorized")


        assert message.from_user is not None
        await bot.delete_state(message.from_user.id, message.chat.id)

    def only_auth_user():
        def decorator(func):
            @wraps(func)
            async def wrapper(message, *args, **kwargs):
                cursor = connection.cursor()
                cursor.execute("SELECT 1 FROM authorized_users WHERE user_id = ?", (message.from_user.id,))
                is_present = cursor.fetchone()
                if is_present is not None:
                    return await func(message, *args, **kwargs)
                else:
                   await bot.send_message(message.chat.id, "You have to be authorzied to use this bot. Ask admin to authorize you.")
            return wrapper
        return decorator

    @bot.message_handler(content_types=["voice"])
    @only_auth_user()
    async def _(message: types.Message):
        assert message.voice is not None
        file_id = message.voice.file_id
        await enqueue_media(file_id, message)

    @bot.message_handler(content_types=["video_note"])
    @only_auth_user()
    async def _(message: types.Message):
        assert message.video_note is not None
        file_id = message.video_note.file_id
        await enqueue_media(file_id, message)

    @bot.message_handler()
    async def _(message: types.Message):
        await bot.send_message(message.chat.id, "I don't care about it. Send me voice or video note that I can transcribe")


    async def enqueue_media(file_id: str, message: types.Message) -> None:
        if queue.full():
            await bot.send_message(message.chat.id, "Service is too busy. Try again later")
            return

        file = await bot.get_file(file_id)

        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            downloaded = await bot.download_file(file.file_path)
            temp_file.write(downloaded)

            try:
                audio_data, _ = (
                    ffmpeg
                    .input(temp_file.name)
                    .output('pipe:', format='f32le', acodec='pcm_f32le', ac=1, ar=16000)
                    .run(capture_stdout=True, capture_stderr=True)
                )
            except ffmpeg.Error:
                raise

        message = await bot.send_message(message.chat.id, reply_to_message_id=message.id, text="Audio file has been received")
        await queue.put((message.chat.id, message.message_id, audio_data))

    await bot.set_my_commands(admin_commands, types.BotCommandScopeChat(admin_chat_id))
    bot.add_custom_filter(asyncio_filters.StateFilter(bot))

    return bot

def create_message_updater(bot: AsyncTeleBot):
    async def update_message(chat_id: int, message_id: int, text: str):
        try:
            await bot.edit_message_text(text=text, chat_id=chat_id, message_id=message_id)
        except:
            logger.exception(f"Failed to update the message")

    return update_message
