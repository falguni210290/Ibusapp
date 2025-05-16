from pydantic import BaseModel

class RegisterRequest(BaseModel):
    name: str
    email: str
    phone: str
    password: str
