from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Message

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        print(f"[LOG] Пользователь {event.from_user.id}: {event.text}")
        return await handler(event, data)
