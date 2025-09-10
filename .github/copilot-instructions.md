# StrataSlims Discord Music Bot

StrataSlims is a Python Discord bot that integrates with the Suno AI music generation API to create custom music based on user prompts. The bot provides Discord slash commands with interactive forms for music generation requests.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Environment Setup
- Set up Python virtual environment:
  - `python3 -m venv .venv` -- takes 3 seconds
  - `source .venv/bin/activate`
  - `pip install --upgrade pip`
- Install dependencies:
  - `pip install -r requirements.txt` -- takes 30-60 seconds normally, NEVER CANCEL. Set timeout to 10+ minutes for network issues.
  - **Network Issues**: If pip install fails due to network timeouts (HTTPSConnectionPool read timed out), this is a known issue with PyPI access in some environments. Document this limitation and retry with: `pip install --timeout=300 --retries=3 -r requirements.txt`
  - **Alternative for Network Issues**: If persistent timeouts occur, focus validation on syntax checking and document that full dependency testing requires network access
- Verify installation:
  - `python -m py_compile *.py` -- validates syntax of all Python files
  - `python main.py` -- should output "Hello from strataslims!" to confirm basic setup

### Development Tools
- Install linting tools for code quality:
  - `pip install flake8` -- takes 15-30 seconds
  - `flake8 --max-line-length=100 --ignore=E501 *.py` -- shows code style issues
- Code has many existing linting violations (whitespace, imports, formatting) - focus on not introducing new ones

### Running the Application
- **IMPORTANT**: Full bot functionality requires environment variables in `.env` file:
  - `DISCORD_BOT_TOKEN` - Discord bot token
  - `TEST_GUILD_ID` - Discord server ID for testing
  - `GREENLIST_USER_IDS` - Comma-separated user IDs allowed to use bot
  - `SUNO_TOKEN` - Suno API token for music generation
  - `WEBHOOK_BOT` - Discord webhook URL for bot messages
  - `WEBHOOK_SEND_TO` - Discord webhook URL for sending results
- Without these environment variables, the bot cannot start but main.py will run
- Run basic functionality: `python main.py`
- Run bot (requires .env setup): `python bot.py` -- will fail without proper tokens

## Validation

### Basic Validation Steps
- ALWAYS run these validation steps after making changes:
  - `python -m py_compile *.py` -- ensures no syntax errors
  - `python main.py` -- verifies basic import structure
  - `flake8 --max-line-length=100 --ignore=E501 <changed_files>` -- check code style of modified files only

### Manual Testing Scenarios
- **Limited Testing Available**: Without Discord API tokens and Suno API access, full functionality cannot be tested
- **Dependency Requirements**: Full import testing requires installing dependencies via pip (discord.py, aiohttp, etc.)
- **Basic Import Testing with Dependencies**: After successful pip install, verify modules import:
  - `python -c "import bot, config, sunoapi; print('All imports successful')"` -- requires Discord tokens in .env
  - `python -c "from config import get_bot_token; print('Config loading works')"` -- tests environment variable loading
- **Syntax-Only Testing**: When dependencies unavailable due to network issues:
  - `python -m py_compile *.py` -- validates Python syntax without imports
  - Focus on code structure validation instead of runtime testing
- **Code Review Focus**: Since runtime testing is limited, focus on:
  - Code syntax and structure validation
  - Import statement correctness
  - Variable naming and function signatures
  - Discord.py API usage patterns

### Environment Variable Testing
- Create a minimal `.env` file for testing imports:
  ```
  DISCORD_BOT_TOKEN=test_token
  TEST_GUILD_ID=123456789
  GREENLIST_USER_IDS=123456789
  SUNO_TOKEN=test_token
  WEBHOOK_BOT=https://discord.com/api/webhooks/test
  WEBHOOK_SEND_TO=https://discord.com/api/webhooks/test
  ```
- Test configuration loading: `python -c "from config import get_bot_token; print('Config loading works')"`
- **Important**: Always remove test .env files before committing to avoid exposing test tokens

### Validation Without Network Access
- **Syntax Validation**: `python -m py_compile *.py` -- works offline, validates all Python syntax
- **Code Structure Check**: `python main.py` -- runs basic functionality without dependencies
- **Dependency Availability Check**: 
  ```python
  python -c "
  try:
      import discord
      print('discord.py available - full bot testing possible')
  except ImportError:
      print('discord.py not available - use syntax-only validation')
  "
  ```
- **Import Chain Analysis**: Review import statements manually for circular dependencies or missing modules
- **Configuration Validation**: Test config.py functions with test environment variables

## Common Tasks

### Repository Structure
```
ls -la
total 88
drwxr-xr-x 6 runner runner  4096 Sep 10 07:28 .
drwxr-xr-x 3 runner runner  4096 Sep 10 07:18 ..
drwxrwxr-x 7 runner runner  4096 Sep 10 07:25 .git
drwxrwxr-x 2 runner runner  4096 Sep 10 07:26 .github
-rw-rw-r-- 1 runner runner   167 Sep 10 07:19 .gitignore
-rw-rw-r-- 1 runner runner     4 Sep 10 07:19 .python-version
drwxrwxr-x 5 runner runner  4096 Sep 10 07:26 .venv
-rw-rw-r-- 1 runner runner     0 Sep 10 07:19 README.md
drwxrwxr-x 2 runner runner  4096 Sep 10 07:27 __pycache__
-rw-rw-r-- 1 runner runner 15012 Sep 10 07:19 bot.py
-rw-rw-r-- 1 runner runner  3477 Sep 10 07:19 config.py
-rw-rw-r-- 1 runner runner    89 Sep 10 07:19 main.py
-rw-rw-r-- 1 runner runner     0 Sep 10 07:19 mock.py
-rw-rw-r-- 1 runner runner  4697 Sep 10 07:19 mockapi.py
-rw-rw-r-- 1 runner runner  3425 Sep 10 07:19 musicparser.py
-rw-rw-r-- 1 runner runner   156 Sep 10 07:19 pyproject.toml
-rw-rw-r-- 1 runner runner   339 Sep 10 07:19 requirements.txt
-rw-rw-r-- 1 runner runner  4070 Sep 10 07:19 sunoapi.py
-rw-rw-r-- 1 runner runner  6986 Sep 10 07:19 sunoresults.py
```

**Note**: .venv and __pycache__ directories are created during development and should be in .gitignore

### Key Project Files
- **bot.py** (319 lines) - Main Discord bot implementation with slash commands and UI components
- **config.py** (100 lines) - Environment variable management and configuration loading
- **sunoapi.py** (126 lines) - Integration with Suno AI music generation API
- **musicparser.py** (100 lines) - Music request parsing and data formatting
- **sunoresults.py** (196 lines) - Processing and handling of Suno API responses
- **main.py** (6 lines) - Simple entry point for basic testing
- **mockapi.py** (130 lines) - Mock API implementations for testing
- **requirements.txt** - Python dependencies (discord.py, aiohttp, requests, etc.)

### Project Dependencies (requirements.txt)
```
aiohappyeyeballs==2.6.1
aiohttp==3.12.15
aiosignal==1.4.0
async-timeout==5.0.1
attrs==25.3.0
certifi==2025.8.3
charset-normalizer==3.4.3
discord-py==2.6.3
frozenlist==1.7.0
idna==3.10
multidict==6.6.4
pip==25.2
propcache==0.3.2
python-dotenv==1.1.1
requests==2.32.5
setuptools==58.1.0
typing-extensions==4.15.0
urllib3==2.5.0
yarl==1.20.1
```

### Python Version Requirements
- **Required**: Python 3.9+ (specified in pyproject.toml)
- **Tested**: Works with Python 3.12
- Check version: `python3 --version`

## Working with the Bot Code

### Discord Bot Architecture
- **MyClient**: Main Discord client class with slash command tree
- **UI Components**: Uses discord.py UI components (buttons, modals, forms)
- **Slash Commands**: `/generate` command for music generation requests
- **Interactive Forms**: Multi-step user input collection for music parameters

### Key Code Patterns
- **Environment Variable Access**: Use functions from `config.py` (get_bot_token(), get_suno_token(), etc.)
- **API Integration**: Async/await patterns for Suno API calls in `sunoapi.py`
- **Discord Interactions**: Button handlers and modal forms for user input
- **Error Handling**: Extensive try/catch blocks for API reliability

### Frequent Modification Areas
- **bot.py**: Discord command handlers and UI interaction logic
- **sunoapi.py**: API call implementations and response handling
- **musicparser.py**: Input validation and payload construction
- **config.py**: Environment variable management

## Limitations and Notes

### Testing Limitations
- **No CI/CD**: No GitHub Actions or automated testing currently set up
- **API Dependencies**: Full functionality requires external API tokens (Discord, Suno)
- **Network Requirements**: Bot needs internet access for Discord and Suno API calls
- **Database**: No persistent storage - all data is transient

### Development Considerations
- **Code Quality**: Many existing linting violations - maintain current style when modifying
- **Environment Variables**: All secrets must be in `.env` file, never committed to git
- **API Rate Limits**: Suno API has credit/rate limiting that affects functionality
- **Discord Permissions**: Bot requires specific Discord permissions for slash commands

### Build and Deployment Notes
- **No Build Process**: Pure Python project, no compilation required
- **Dependencies Only**: Main setup step is installing Python packages
- **Runtime Configuration**: All configuration via environment variables
- **Simple Deployment**: Can run anywhere Python 3.9+ and dependencies are available

### Time Expectations
- **Virtual Environment Creation**: ~3 seconds
- **Dependency Installation**: 30-60 seconds (can take up to 10 minutes with network issues)
- **Code Compilation Check**: <5 seconds
- **Linting**: ~10 seconds for full codebase
- **NEVER CANCEL**: Always wait for pip installations and dependency resolution to complete