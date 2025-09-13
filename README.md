# StrataSlims

StrataSlims is a Discord bot that generates music using Suno AI with Model Context Protocol (MCP) support. This bot allows users to create custom music tracks through Discord commands and provides an MCP server interface for integration with AI systems.

## Features

- 🎵 **Music Generation**: Generate custom music tracks using Suno AI
- 🤖 **Discord Bot**: Interactive Discord bot with slash commands
- 🔌 **MCP Support**: Model Context Protocol server for AI integration
- 🎨 **Music Parsing**: Intelligent parsing of music generation requests
- 💰 **Credit Management**: Monitor Suno AI API credits
- 🛡️ **Access Control**: Configurable user access control (greenlist)

## Prerequisites

- Python 3.9 or higher
- Discord Bot Token
- Suno AI API access
- Discord server with appropriate permissions

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Kor-ok/StrataSlims.git
   cd StrataSlims
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the project root:
   ```env
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   SUNO_API_KEY=your_suno_api_key_here
   TEST_GUILD_ID=your_discord_guild_id_here
   GREENLIST=comma,separated,user,ids
   ```

## Configuration

### Discord Bot Setup

1. Create a Discord application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a bot and copy the token to your `.env` file
3. Enable the following bot permissions:
   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Attach Files

### Suno AI Setup

1. Get API access from Suno AI
2. Add your API key to the `.env` file
3. Configure credit limits and usage policies

## Usage

### Running the Discord Bot

```bash
python main.py
```

### Running the MCP Server

The MCP server provides a standardized interface for AI systems to interact with StrataSlims:

```bash
python mcp_server.py
```

### Discord Commands

- `/generate` - Generate music with a text prompt
- `/credits` - Check remaining Suno AI credits
- `/help` - Display available commands

### MCP Tools

When running as an MCP server, StrataSlims provides these tools:

- **generate_music**: Generate music using Suno AI API
- **check_credits**: Check remaining Suno AI credits  
- **parse_music_request**: Parse and validate music generation requests

## Deployment

The bot is currently hosted on Google Compute Engine with the following configuration:

- Instance: e2-micro (2 vCPUs, 1 GB memory)
- OS image: debian-12-bookworm-v20240611
- Cost: no running cost (fits within current free tier/credits)
- Notes:
  - The e2-micro has limited memory. Avoid running additional heavy processes on the same VM.
  - Prefer running the bot and MCP server as separate processes if needed, but be mindful of RAM limits.
  - Use swap or lightweight process managers (e.g., systemd) if stability issues arise under memory pressure.

Basic start commands (example):

```bash
# From project root on the VM
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run bot
python main.py

# Run MCP server (optional)
python mcp_server.py
```

## MCP Configuration

To use StrataSlims as an MCP server, add this configuration to your MCP client:

```json
{
  "mcpServers": {
    "strataslims": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

## Project Structure

```
StrataSlims/
├── bot.py              # Discord bot implementation
├── mcp_server.py       # MCP server implementation
├── config.py           # Configuration management
├── musicparser.py      # Music request parsing
├── sunoapi.py          # Suno AI API integration
├── sunoresults.py      # Result processing
├── mockapi.py          # Mock API for testing
├── main.py             # Application entry point
├── mcp.json            # MCP server configuration
├── pyproject.toml      # Project metadata
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## API Integration

### Suno AI

StrataSlims integrates with the Suno AI API for music generation. Key features:

- Asynchronous music generation
- Credit monitoring
- Progress tracking
- Result retrieval

### Discord API

Using discord.py for:

- Slash command handling
- Message management
- File uploads
- User authentication

## Development

### Setting up Development Environment

1. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run tests (if available):
   ```bash
   python -m pytest
   ```

3. Code formatting:
   ```bash
   black .
   flake8 .
   ```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_BOT_TOKEN` | Discord bot token | Yes |
| `SUNO_API_KEY` | Suno AI API key | Yes |
| `TEST_GUILD_ID` | Discord guild ID for testing | Yes |
| `GREENLIST` | Comma-separated user IDs allowed to use the bot | No |

## Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check Discord token validity
   - Verify bot permissions in Discord server
   - Check network connectivity

2. **Music generation fails**
   - Verify Suno AI API key
   - Check remaining credits
   - Validate prompt format

3. **MCP server connection issues**
   - Ensure Python path is correct
   - Check MCP configuration format
   - Verify server startup

### Logging

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- Create an issue on [GitHub](https://github.com/Kor-ok/StrataSlims/issues)
- Check the documentation
- Review existing issues for solutions

## Acknowledgments

- [Discord.py](https://discordpy.readthedocs.io/) - Discord API wrapper
- [Suno AI](https://suno.ai/) - Music generation API
- [Model Context Protocol](https://modelcontextprotocol.io/) - Standardized AI integration