from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DealTracker API"
    api_prefix: str = "/api"
    environment: str = "dev"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    twilio_auth_token: str = ""
    twilio_account_sid: str = ""
    twilio_whatsapp_number: str = ""
    mistral_api_key: str = ""
    mistral_transcribe_model: str = "mistral-voxtral-mini-transcribe-v2"
    openai_api_key: str = ""
    openai_nlu_model: str = "gpt-5-mini"

    model_config = SettingsConfigDict(env_file=(".env.local", ".env"), env_file_encoding="utf-8")


settings = Settings()
