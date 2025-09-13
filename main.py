#!/usr/bin/env python3
"""
StrataSlims - Discord Music Generation Bot

Main entry point for the StrataSlims Discord bot with Suno AI integration.
"""

import asyncio
import sys
import os
from pathlib import Path

def main():
    """Main function to start the StrataSlims bot."""
    print("Starting StrataSlims Discord Bot...")
    
    # Check if .env file exists
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        print("Warning: No .env file found.")
        if env_example.exists():
            print("Please copy .env.example to .env and configure your settings.")
        else:
            print("Please create a .env file with your Discord bot token and other settings.")
        print("\nRequired environment variables:")
        print("- DISCORD_BOT_TOKEN: Your Discord bot token")
        print("- TEST_GUILD_ID: Your Discord server ID")
        print("- SUNO_API_KEY: Your Suno AI API key")
        print("\nFor a complete example, see the README.md file.")
        return
    
    try:
        # Import bot components after env check
        from bot import StrataSlims
        from config import get_bot_token
        
        # Get bot token from configuration
        token = get_bot_token()
        
        if not token:
            print("Error: No Discord bot token found. Please check your .env file.")
            print("Make sure DISCORD_BOT_TOKEN is set in your environment variables.")
            sys.exit(1)
        
        # Create and run the Discord client
        client = StrataSlims()
        client.run(token)
        
    except KeyboardInterrupt:
        print("\nBot shutdown initiated by user.")
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"Error starting bot: {e}")
        print("Please check your configuration and try again.")
        print("Make sure all required environment variables are set in your .env file.")

if __name__ == "__main__":
    main()
