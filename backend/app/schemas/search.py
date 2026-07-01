from pydantic import BaseModel


class PlateSearch(BaseModel):
    plate_number: str