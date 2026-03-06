import asyncio
import logging

import whisper
import numpy as np
from concurrent.futures import ProcessPoolExecutor


logger = logging.getLogger(__name__)

executor = ProcessPoolExecutor(max_workers=1)

async def transcription_worker(queue: asyncio.Queue, send_message, model):
    logger.info("worker starts")

    loop = asyncio.get_running_loop()
    while True:
        chat_id, message_id, audio_bytes = await queue.get()
        audio_np = np.frombuffer(audio_bytes, dtype=np.float32)

        await send_message(
                chat_id=chat_id,
                message_id=message_id,
                text="Transcribing"
            )

        try:
            result = await loop.run_in_executor(executor, transcribe, audio_np, model)
            if result == "":
                result = "I can't hear anything"
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            result = "Error while transcribing a message"
            continue

        await send_message(
            chat_id=chat_id,
            message_id=message_id,
            text=result
        )
        queue.task_done()

def init_model(model_name):
    return whisper.load_model(model_name)

def transcribe(file, model):
    result = model.transcribe(file, fp16=False)
    return result["text"]
