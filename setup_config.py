#!/usr/bin/env python3
"""
Configuration utility for Hotel Voice AI Concierge
Helps set up and validate environment configuration
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings, print_configuration_status, validate_required_keys

def create_env_file():
    """Create a .env file from the example template"""
    env_example_path = Path(__file__).parent.parent / ".env.example"
    env_path = Path(__file__).parent.parent / ".env"
    
    if env_path.exists():
        overwrite = input("⚠️  .env file already exists. Overwrite? (y/N): ").lower()
        if overwrite != 'y':
            print("Keeping existing .env file")
            return False
    
    if env_example_path.exists():
        with open(env_example_path, 'r') as f:
            content = f.read()
        
        with open(env_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Created .env file from template")
        print(f"📝 Please edit {env_path} and add your API keys")
        return True
    else:
        print("❌ .env.example template not found")
        return False

def check_api_keys():
    """Check which API keys are set and which are missing"""
    print("🔑 API Key Status:")
    print("-" * 40)
    
    api_keys = [
        ("Soniox STT", "SONIOX_API_KEY", settings.voice.soniox_api_key),
        ("Perplexity Sonar Pro", "PERPLEXITY_API_KEY", settings.voice.perplexity_api_key),
        ("Cartesia TTS", "CARTESIA_API_KEY", settings.voice.cartesia_api_key),
        ("Deepgram STT (fallback)", "DEEPGRAM_API_KEY", settings.voice.deepgram_api_key),
        ("OpenAI (fallback)", "OPENAI_API_KEY", settings.voice.openai_api_key),
        ("Daily.co Transport", "DAILY_API_KEY", settings.daily.daily_api_key),
    ]
    
    for service, env_var, value in api_keys:
        status = "✅ Set" if value else "❌ Missing"
        print(f"  {service:<25} {env_var:<20} {status}")
    
    print(f"\n🗄️  Database:")
    db_status = "✅ Set" if settings.database.database_url else "❌ Missing"
    print(f"  PostgreSQL            DATABASE_URL         {db_status}")
    
    print(f"\n📞 Room URL:")
    room_status = "✅ Set" if settings.daily.daily_room_url else "❌ Missing"
    print(f"  Daily Room            DAILY_ROOM_URL       {room_status}")

def setup_wizard():
    """Interactive setup wizard"""
    print("🧙‍♂️ Hotel Voice AI Concierge Setup Wizard")
    print("=" * 50)
    
    # Check if .env exists
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print("📝 No .env file found. Let's create one!")
        create_env_file()
        print("\n⚠️  Please edit the .env file with your API keys, then run this script again.")
        return
    
    print("\n📊 Current Configuration Status:")
    print_configuration_status()
    
    required_keys, warnings = validate_required_keys()
    
    if required_keys:
        print(f"\n❌ Missing required configuration:")
        for key in required_keys:
            print(f"  - {key}")
        print(f"\n📝 Please edit {env_path} to add the missing keys.")
        
        # Offer to open the file
        if input("\n🔧 Open .env file for editing? (y/N): ").lower() == 'y':
            try:
                os.system(f"open {env_path}")  # macOS
            except:
                try:
                    os.system(f"xdg-open {env_path}")  # Linux
                except:
                    print(f"Please manually open: {env_path}")
    else:
        print(f"\n✅ Configuration is complete!")
        print(f"\n🚀 You're ready to run the hotel voice AI concierge!")
        print(f"\nNext steps:")
        print(f"  1. Set up your database: python scripts/seed_database.py")
        print(f"  2. Start the API server: python -m uvicorn app.main:app --reload")
        print(f"  3. Test the voice pipeline: python hotel_room_service_simplified.py")

def main():
    """Main CLI function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            print_configuration_status()
        elif command == "keys":
            check_api_keys()
        elif command == "create-env":
            create_env_file()
        elif command == "setup":
            setup_wizard()
        else:
            print("Available commands:")
            print("  status     - Show configuration status")
            print("  keys       - Check API key status")
            print("  create-env - Create .env file from template")
            print("  setup      - Run interactive setup wizard")
    else:
        setup_wizard()

if __name__ == "__main__":
    main()