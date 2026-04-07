from pydantic import BaseModel, Field
from typing import Optional, Union

class JournalLogBase(BaseModel):
    day: str
    timeChunk: str
    intention: Optional[str] = ""
    actual: str
    feeling: Optional[str] = ""
    brainFog: Optional[Union[int, str]] = 0
    isValuableDetour: Optional[bool] = False
    inventoryNote: Optional[str] = ""
    reflection: Optional[str] = ""

class JournalRequestSchema(BaseModel):
    journal_entry: str = Field(..., max_length=10000)
    log_data: JournalLogBase

class CalendarRequestSchema(BaseModel):
    date: Optional[str] = None

class DailyReflectionLogData(BaseModel):
    day: str

class DailyReflectionRequestSchema(BaseModel):
    journal_entry: str = Field(..., max_length=15000)
    log_data: DailyReflectionLogData
