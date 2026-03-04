import os
import logging
import asyncio
import sqlite3

from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from transcriber.transcriber import transcription_worker
from bot.bot import init, create_message_updater

TELEGRAM_API_KEY_ENV = "BOT_TOKEN"
ADMIN_CHAT_ID_ENV = "ADMIN_CHAT_ID"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    bot_token = os.environ[TELEGRAM_API_KEY_ENV]
    admin_chat_id = os.environ[ADMIN_CHAT_ID_ENV]

    media_queue = asyncio.Queue(maxsize=50)

    with sqlite3.connect("bot.db") as connection:
        cursor = connection.cursor()
        auth_users_query = '''
            CREATE TABLE IF NOT EXISTS authorized_users(
            user_id NUMBER PRIMARY KEY
            );
        '''
        cursor.execute(auth_users_query)
        connection.commit()

        bot = AsyncTeleBot(bot_token, state_storage=StateMemoryStorage())
        bot = await init(bot, int(admin_chat_id), connection, media_queue)

        transcribe_task = asyncio.create_task(transcription_worker(media_queue, create_message_updater(bot)))

        await bot.polling()

        await media_queue.join()
        await transcribe_task

if __name__ == "__main__":
    asyncio.run(main())
