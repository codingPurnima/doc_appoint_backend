from pydantic_settings import BaseSettings
# here, to access env file data, we don't need load_dotenv() because BaseSettings already does that for us

class Settings(BaseSettings):
    DOCTOR_REGISTER_SECRET: str 
    DATABASE_URL: str
    SECRET_KEY: str

    class Config:
        env_file=".env"

settings = Settings()
