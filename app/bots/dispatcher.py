from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

def make_dp() -> Dispatcher:
    return Dispatcher(storage=MemoryStorage())