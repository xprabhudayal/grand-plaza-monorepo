"""
Configuration management for Hotel Voice AI Concierge
Centralizes all environment variables and configuration settings
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Main settings class with all configuration"""
    
    # Voice pipeline configuration
    soniox_api_key: Optional[str] = Field(None, env="SONIOX_API_KEY")
    perplexity_api_key: Optional[str] = Field(None, env="PERPLEXITY_API_KEY")
    groq_api_key: Optional[str] = Field(None, env="GROQ_API_KEY")
    cartesia_api_key: Optional[str] = Field(None, env="CARTESIA_API_KEY")
    deepgram_api_key: Optional[str] = Field(None, env="DEEPGRAM_API_KEY")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    
    voice_timeout: int = Field(120, env="VOICE_TIMEOUT")
    max_conversation_duration: int = Field(600, env="MAX_CONVERSATION_DURATION")
    interruption_enabled: bool = Field(True, env="INTERRUPTION_ENABLED")
    
    # Database configuration
    database_url: str = Field("file:./database.db", env="DATABASE_URL")
    
    # Daily.co transport configuration
    daily_api_key: Optional[str] = Field(None, env="DAILY_API_KEY")
    daily_room_url: Optional[str] = Field(None, env="DAILY_ROOM_URL")
    
    # FastAPI application settings
    app_name: str = Field("Hotel Voice AI Concierge", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    debug: bool = Field(False, env="DEBUG")
    
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    
    secret_key: str = Field("change-me-in-production", env="SECRET_KEY")
    
    # CORS settings
    cors_origins: str = Field("*", env="CORS_ORIGINS")  # Changed from List[str] to str
    cors_allow_credentials: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    
    # Logging configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("text", env="LOG_FORMAT")  # text or json
    
    # Hotel-specific configuration
    hotel_name: str = Field("Grand Plaza Hotel", env="HOTEL_NAME")
    hotel_phone: str = Field("+1-555-0123", env="HOTEL_PHONE")
    room_service_hours: str = Field("24/7", env="ROOM_SERVICE_HOURS")
    
    # Guest context
    guest_room_number: Optional[str] = Field(None, env="GUEST_ROOM_NUMBER")
    
    # Order settings
    max_order_items: int = Field(20, env="MAX_ORDER_ITEMS")
    default_preparation_time: int = Field(25, env="DEFAULT_PREPARATION_TIME")
    delivery_time_buffer: int = Field(10, env="DELIVERY_TIME_BUFFER")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS origins string to list"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings

def validate_required_keys():
    """Validate that required API keys are present"""
    required_keys = []
    warnings = []
    
    # Check for at least one STT service
    if not settings.soniox_api_key and not settings.deepgram_api_key:
        required_keys.append("SONIOX_API_KEY or DEEPGRAM_API_KEY")
    
    # Check for at least one LLM service
    if not settings.perplexity_api_key and not settings.openai_api_key:
        required_keys.append("PERPLEXITY_API_KEY or OPENAI_API_KEY")
    
    # Check for TTS service
    if not settings.cartesia_api_key:
        required_keys.append("CARTESIA_API_KEY")
    
    # Check for database
    if not settings.database_url:
        required_keys.append("DATABASE_URL")
    
    # Check for Daily transport (if using voice)
    if not settings.daily_room_url:
        warnings.append("DAILY_ROOM_URL not set - voice features will be disabled")
    
    # Warnings for fallback services
    if settings.soniox_api_key and not settings.deepgram_api_key:
        warnings.append("Consider setting DEEPGRAM_API_KEY as STT fallback")
    
    if settings.perplexity_api_key and not settings.openai_api_key:
        warnings.append("Consider setting OPENAI_API_KEY as LLM fallback")
    
    return required_keys, warnings

def print_configuration_status():
    """Print current configuration status"""
    print("🏨 Hotel Voice AI Concierge - Configuration Status")
    print("=" * 60)
    
    # Voice services
    print("\n🎤 Voice Services:")
    print(f"  STT: {'✅ Soniox' if settings.soniox_api_key else ('✅ Deepgram' if settings.deepgram_api_key else '❌ None')}")
    print(f"  LLM: {'✅ Perplexity Sonar Pro' if settings.perplexity_api_key else ('✅ OpenAI' if settings.openai_api_key else '❌ None')}")
    print(f"  TTS: {'✅ Cartesia' if settings.cartesia_api_key else '❌ None'}")
    
    # Transport
    print(f"\n📞 Transport:")
    print(f"  Daily.co: {'✅ Configured' if settings.daily_room_url else '❌ Not configured'}")
    
    # Database
    print(f"\n💾 Database:")
    print(f"  SQLite: {'✅ Configured' if settings.database_url else '❌ Not configured'}")
    
    # Hotel info
    print(f"\n🏨 Hotel Configuration:")
    print(f"  Name: {settings.hotel_name}")
    print(f"  Phone: {settings.hotel_phone}")
    print(f"  Room Service: {settings.room_service_hours}")
    if settings.guest_room_number:
        print(f"  Current Room: {settings.guest_room_number}")
    
    # Check for issues
    required_keys, warnings = validate_required_keys()
    
    if required_keys:
        print(f"\n❌ Missing Required Configuration:")
        for key in required_keys:
            print(f"  - {key}")
    
    if warnings:
        print(f"\n⚠️  Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not required_keys and not warnings:
        print(f"\n✅ All configuration looks good!")
    
    print("=" * 60)

if __name__ == "__main__":
    print_configuration_status()