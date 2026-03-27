from pydantic import BaseModel, Field


class UserMapping(BaseModel):
    id: str
    full_name: str
    email: str
    whatsapp_number: str | None = Field(default=None, pattern=r"^\+[1-9]\d{6,14}$")


class UserMappingUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    whatsapp_number: str = Field(pattern=r"^\+[1-9]\d{6,14}$")
