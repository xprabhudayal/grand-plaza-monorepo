#!/usr/bin/env python3
"""
Launch script for Hotel Voice AI Concierge
Validates configuration and starts the appropriate service
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config.settings import settings, validate_required_keys, print_configuration_status

def check_prerequisites():
    """Check if all prerequisites are met"""
    required_keys, warnings = validate_required_keys()
    
    if required_keys:
        print("❌ Missing required configuration:")
        for key in required_keys:
            print(f"  - {key}")
        print("\n🔧 Run: python setup_config.py setup")
        return False
    
    if warnings:
        print("⚠️  Configuration warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        print()
    
    return True

def launch_api_server():
    """Launch the FastAPI server"""
    print("🚀 Starting Hotel Voice AI Concierge API Server...")
    print(f"📡 Server will run on http://{settings.api_host}:{settings.api_port}")
    print("📚 API docs available at http://localhost:8000/docs")
    print("\n🔄 Starting server...")
    
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.debug,
            log_level=settings.log_level.lower()
        )
    except ImportError:
        print("❌ uvicorn not installed. Install with: pip install uvicorn")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")

def launch_voice_pipeline():
    """Launch the voice AI pipeline"""
    print("🎙️  Starting Hotel Voice AI Pipeline...")
    
    if not settings.daily_room_url:
        print("❌ DAILY_ROOM_URL not configured")
        print("🔧 Set up Daily.co room URL to use voice features")
        return
    
    try:
        # Import and run the voice pipeline
        from hotel_room_service_simplified import main
        asyncio.run(main())
    except ImportError as e:
        print(f"❌ Missing dependencies for voice pipeline: {e}")
        print("💡 Install required packages")
    except Exception as e:
        print(f"❌ Failed to start voice pipeline: {e}")

def seed_database():
    """Seed the database with menu data"""
    print("🌱 Seeding database with menu data...")
    
    try:
        from scripts.seed_database import seed_menu_data, create_sample_guest
        seed_menu_data()
        create_sample_guest()
        print("✅ Database seeded successfully!")
    except Exception as e:
        print(f"❌ Failed to seed database: {e}")

def show_menu():
    """Display the hotel menu"""
    print("📋 Displaying hotel menu...")
    
    try:
        from scripts.menu_display import display_full_menu
        display_full_menu()
    except Exception as e:
        print(f"❌ Failed to display menu: {e}")

def main():
    """Main launcher function"""
    print("🏨 Hotel Voice AI Concierge Launcher")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "config":
            print_configuration_status()
            return
        elif command == "api":
            if check_prerequisites():
                launch_api_server()
            return
        elif command == "voice":
            if check_prerequisites():
                launch_voice_pipeline()
            return
        elif command == "seed":
            seed_database()
            return
        elif command == "menu":
            show_menu()
            return
        elif command == "help":
            pass  # Show help below
        else:
            print(f"❌ Unknown command: {command}")
    
    # Show help
    print("Available commands:")
    print("  config  - Show configuration status")
    print("  api     - Start the FastAPI server")
    print("  voice   - Start the voice AI pipeline")  
    print("  seed    - Seed database with menu data")
    print("  menu    - Display the hotel menu")
    print("  help    - Show this help message")
    print("")
    print("Examples:")
    print("  python launch.py config")
    print("  python launch.py api")
    print("  python launch.py voice")

if __name__ == "__main__":
    main()