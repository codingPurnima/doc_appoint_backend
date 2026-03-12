from pydantic_settings import BaseSettings
# here, to access env file data, we don't need load_dotenv() because BaseSettings already does that for us

class Settings(BaseSettings):
    DOCTOR_REGISTER_SECRET: str 
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str= 'HS256'   
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    class Config:
        env_file=".env"

settings = Settings()
# now you can import this instance everywhere in the folder to access the environment variables without having to use os, load_dotenv, etc. 