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
    openai_api_key: str = ""
    openai_nlu_model: str = "gpt-5-mini"
    openai_transcribe_model: str = "whisper-1"
    email_provider: str = "auto"
    graph_tenant_id: str = ""
    graph_client_id: str = ""
    graph_client_secret: str = ""
    graph_sender_user: str = ""
    graph_timeout_seconds: int = 20
    graph_fallback_to_smtp: bool = True
    summary_alert_webhook_url: str = ""
    summary_alert_timeout_seconds: int = 5
    rate_limit_window_seconds: int = 60
    twilio_rate_limit_per_phone: int = 25
    summary_send_rate_limit_per_user: int = 6
    deals_import_rate_limit_per_user: int = 4
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_starttls_enabled: bool = True
    smtp_ssl_enabled: bool = False
    smtp_timeout_seconds: int = 20
    weekly_summary_scheduler_enabled: bool = True
    weekly_summary_timezone: str = "Europe/Brussels"
    weekly_summary_day_of_week: str = "mon"
    weekly_summary_hour: int = 8
    weekly_summary_minute: int = 0
    weekly_summary_cron_token: str = ""
    frontend_app_url: str = ""

    model_config = SettingsConfigDict(env_file=(".env.local", ".env"), env_file_encoding="utf-8", extra="ignore")


settings = Settings()
