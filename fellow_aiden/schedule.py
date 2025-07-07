"""Model to validate the coffee schedule data"""
from pydantic import BaseModel, field_validator, ValidationError
from typing import List
import re

# Regular expression for profileId: either "p" followed by digits or "plocal" followed by digits
PROFILE_ID_REGEX = re.compile(r'^(p|plocal)\d+$')

class CoffeeSchedule(BaseModel):
    days: List[bool]
    secondFromStartOfTheDay: int
    enabled: bool
    amountOfWater: int
    profileId: str

    @field_validator('days')
    @classmethod
    def validate_days(cls, v):
        if len(v) != 7:
            raise ValueError("The 'days' list must contain exactly 7 boolean values (from Sunday to Saturday).")
        if any(not isinstance(day, bool) for day in v):
            raise ValueError("Each element in 'days' must be a boolean.")
        return v

    @field_validator('secondFromStartOfTheDay')
    @classmethod
    def validate_second_from_start_of_the_day(cls, v):
        if not (0 <= v < 86400):
            raise ValueError("secondFromStartOfTheDay must be between 0 and 86399 (seconds in a day).")
        return v

    @field_validator('amountOfWater')
    @classmethod
    def validate_amount_of_water(cls, v):
        if not (150 <= v <= 1500):
            raise ValueError("amountOfWater must be between 150 and 1500.")
        return v

    @field_validator('profileId')
    @classmethod
    def validate_profile_id(cls, v):
        if not PROFILE_ID_REGEX.match(v):
            raise ValueError("profileId must be either 'p' followed by a number or 'plocal' followed by a number.")
        return v