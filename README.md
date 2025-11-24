# News Aggregator

A multi-source news aggregation and synthesis system using LLMs for intelligent analysis. Collects articles from RSS feeds and generates comprehensive, balanced summaries that identify common themes, unique perspectives, sentiment, and potential biases across different sources.

## Features (Sprint 1+)

- **Multi-source RSS Fetching**: Collect articles from multiple RSS feeds
- **Multi-LLM Support**: Choose between OpenAI GPT, Google Gemini, or Anthropic Claude
- **Automatic Fallback**: If one LLM is unavailable, automatically falls back to another
- **Robust Error Handling**: Graceful handling of failed sources and API errors
- **Cost Tracking**: Monitor LLM API costs and token usage across all providers
- **Comprehensive Logging**: Track all operations with detailed metrics
- **JSON Storage**: Save analyses and raw articles for later retrieval
- **Markdown Output**: Generate readable reports
- **CLI Interface**: Easy-to-use command-line interface

## Architecture

```
news-aggregator/
├── core/
│   ├── base.py         # Abstract base classes and Pipeline
│   ├── errors.py       # Custom exception classes
│   └── logger.py       # Logging and metrics tracking
├── components/
│   ├── rss.py          # RSS fetcher
│   ├── llm.py          # Claude LLM processor
│   ├── storage.py      # JSON storage
│   └── output.py       # Markdown output generator
├── data/               # Stored data (created automatically)
├── outputs/            # Generated markdown files (created automatically)
├── logs/               # Application logs (created automatically)
├── config.py           # Configuration management
├── main.py             # CLI application
└── requirements.txt    # Python dependencies
```

## Installation

### Prerequisites

- Python 3.8 or higher
- **At least one LLM API key**:
  - OpenAI API key (https://platform.openai.com/api-keys) - Recommended, works out of the box
  - Google Gemini API key (https://makersuite.google.com/app/apikey) - Free tier available
  - Anthropic Claude API key (https://console.anthropic.com/)

### Option 1: GitHub Codespaces (Recommended)

GitHub Codespaces provides a cloud development environment with zero setup:

1. **Set up API keys as GitHub Secrets:**
   - Go to https://github.com/settings/codespaces
   - Under "Codespaces secrets", click **"New secret"**
   - Add **at least one** of these secrets:
     - `OPENAI_API_KEY` - Your OpenAI API key (recommended)
     - `GEMINI_API_KEY` - Your Google Gemini API key
     - `ANTHROPIC_API_KEY` - Your Anthropic Claude API key
   - For each secret, set repository access to your `aggregator` repository

2. **Create Codespace:**
   - Go to your repository on GitHub
   - Click green **"Code"** button → **"Codespaces"** → **"Create codespace on master"**
   - Wait ~30 seconds for environment to start

3. **Install dependencies in Codespace terminal:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Test the installation:**
   ```bash
   python main.py test
   ```

**Note:** Your API key is automatically available in Codespaces from GitHub Secrets. No `.env` file needed!

### Option 2: Local Installation

If you prefer to run locally:

1. **Clone or download the repository**

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv

   # On Windows:
   venv\Scripts\activate

   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   # Copy the example file
   cp .env.example .env

   # Edit .env and add your API key
   # On Windows, you can use: copy .env.example .env
   ```

   Edit `.env` and set at least one API key:
   ```
   # Add at least one of these:
   OPENAI_API_KEY=sk-your-openai-key-here
   GEMINI_API_KEY=your-gemini-key-here
   ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

   # Optional: Specify which LLM provider to use (default: openai)
   DEFAULT_LLM_PROVIDER=openai  # Options: openai, gemini, anthropic
   ```

5. **Test the installation**:
   ```bash
   python main.py test
   ```

## Usage

### Basic Analysis

Analyze news on a specific topic:

```bash
python main.py analyze "AI regulation in the EU"
```

### Specify Sources

Use specific RSS feeds:

```bash
python main.py analyze "Climate change" -s https://www.bbc.com/news/rss.xml
```

Multiple sources:

```bash
python main.py analyze "Tech startups" \
  -s https://techcrunch.com/feed/ \
  -s https://www.wired.com/feed/rss
```

### Use Source Categories

Use predefined source categories:

```bash
# Estonian sources (default)
python main.py analyze "Estonian politics"

# International sources
python main.py analyze "Global economy" -c international

# Tech sources
python main.py analyze "AI developments" -c tech

# All sources
python main.py analyze "Climate summit" -c all
```

### List Available Sources

```bash
python main.py list-sources
python main.py list-sources -c international
```

### View History

```bash
# Show recent analyses
python main.py history

# Show last 20 analyses
python main.py history -n 20
```

### View Specific Analysis

```bash
python main.py show 20241124_153045_ai_regulation
```

### Additional Options

```bash
# Skip storage (don't save to database)
python main.py analyze "Topic" --no-storage

# Skip output file generation
python main.py analyze "Topic" --no-output

# Verbose logging
python main.py analyze "Topic" -v
```

### View Configuration

```bash
python main.py config
```

## Configuration

Edit `.env` to customize settings:

```bash
# LLM Provider (options: openai, gemini, anthropic)
DEFAULT_LLM_PROVIDER=openai

# Optional: Specific model (auto-selected if not set)
# DEFAULT_LLM_MODEL=gpt-4o-mini

# Maximum tokens for LLM response
MAX_TOKENS=4096

# Maximum articles to fetch per source
MAX_ARTICLES_PER_SOURCE=10

# Directories
DATA_DIR=data
OUTPUT_DIR=outputs
LOG_DIR=logs
```

### Available Models by Provider:

**OpenAI (Default)**
- `gpt-4o-mini` - Fastest, cheapest ($0.15/1M input tokens)
- `gpt-4o` - Better quality ($2.50/1M input tokens)

**Google Gemini**
- `gemini-1.5-flash` - Very fast and cheap ($0.075/1M input tokens)
- `gemini-1.5-pro` - Better quality ($1.25/1M input tokens)

**Anthropic Claude**
- `claude-3-haiku-20240307` - Fast and affordable ($0.25/1M input tokens)
- `claude-3-5-sonnet-20241022` - Best quality ($3/1M input tokens)

## Cost Estimates

**Per analysis (10 articles from 3 sources):**

| Provider | Cheap Model | Cost/Analysis | Premium Model | Cost/Analysis |
|----------|-------------|---------------|---------------|---------------|
| **Gemini** | 1.5-flash | ~$0.005-0.01 | 1.5-pro | ~$0.08-0.15 |
| **OpenAI** | gpt-4o-mini | ~$0.01-0.03 | gpt-4o | ~$0.15-0.30 |
| **Claude** | Haiku | ~$0.02-0.05 | Sonnet | ~$0.20-0.40 |

**Recommendation:** Start with **Gemini 1.5-flash** (cheapest) or **GPT-4o-mini** (best value).

Check `logs/metrics_*.json` for actual costs.

## Output

Each analysis generates:

1. **Markdown file** in `outputs/` directory:
   - Formatted report with all findings
   - Includes metadata and source information

2. **JSON storage** in `data/` directory:
   - `data/syntheses/`: Analysis results
   - `data/raw/`: Raw article data
   - `data/index.json`: Searchable index

3. **Logs** in `logs/` directory:
   - Session logs with all operations
   - Metrics JSON with costs and performance

## Example Output Structure

The synthesis includes:

- **Common Themes**: What multiple sources agree on
- **Source-Specific Perspectives**: Unique information from each source
- **Sentiment Analysis**: Tone and sentiment of each source
- **Potential Biases**: Detected biases or editorial slants
- **Comprehensive Synthesis**: Balanced summary incorporating all perspectives
- **Key Takeaways**: 3-5 bullet points of important insights

## Troubleshooting

### "No LLM API keys found"
- Make sure you've set at least one API key in `.env` or GitHub Secrets
- Supported keys: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`
- In Codespaces, check https://github.com/settings/codespaces
- Locally, verify `.env` file exists in project root

### "No articles fetched from any source"
- Check your internet connection
- Verify RSS feed URLs are valid
- Some feeds may be temporarily down - try different sources

### "Rate limit exceeded"
- You've hit Anthropic's API rate limit
- Wait a few minutes and retry
- Consider upgrading your API plan

### Import errors
- Make sure you've activated your virtual environment
- Run `pip install -r requirements.txt` again

## Future Enhancements (Roadmap)

- **Sprint 2**: Multi-language support with translation
- **Sprint 3**: SQLite/PostgreSQL database
- **Sprint 4**: Web scraping (HTML, PDF support)
- **Sprint 5**: Multi-LLM comparison (Claude + GPT-4 + Gemini)
- **Sprint 6**: Scheduled monitoring with cron jobs
- **Sprint 7**: Cost optimization with intelligent routing
- **Sprint 8**: Web UI with FastAPI + HTMX
- **Sprint 9**: Analytics and trend detection
- **Sprint 10**: Alerts and public API

## Development

The architecture is designed for iterative development:

- **Modular components**: Each component is independent and swappable
- **Abstract base classes**: Easy to add new implementations
- **Proper error handling**: Graceful failure with detailed logging
- **Cost tracking**: Monitor expenses from day 1

To add a new component:

1. Inherit from the appropriate base class in `core/base.py`
2. Implement required abstract methods
3. Register in the pipeline in `main.py`

## License

MIT License - feel free to use and modify

## Contributing

This is a personal project, but feedback and suggestions are welcome!

## Contact

For questions or issues, please open an issue on GitHub.

---

**Built with**: Python, OpenAI GPT / Google Gemini / Anthropic Claude, Typer, Rich
