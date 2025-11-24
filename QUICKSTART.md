# Quick Start Guide

Get your News Aggregator running in 5 minutes!

## Step 1: Setup Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 3: Configure API Key

```bash
# Copy the example environment file
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/Mac
```

Edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
```

Get your API key at: https://console.anthropic.com/

## Step 4: Test Installation

```bash
python main.py test
```

You should see:
- ✓ Configuration valid
- Articles being fetched
- LLM processing
- ✓ All components working!

## Step 5: Run Your First Analysis

```bash
python main.py analyze "AI regulation in Estonia"
```

This will:
1. Fetch articles from Estonian news sources
2. Process them with Claude
3. Generate a synthesis with analysis
4. Save results to `outputs/` folder
5. Store data in `data/` folder

## What's Next?

### Try different topics:
```bash
python main.py analyze "Climate change policy"
python main.py analyze "Tech startups in Baltics"
```

### Use international sources:
```bash
python main.py analyze "EU elections" -c international
```

### View your analysis history:
```bash
python main.py history
```

### Check costs and metrics:
```bash
# Look in logs/ directory
cat logs/metrics_*.json
```

## Common Commands

```bash
# List available sources
python main.py list-sources

# Analyze with specific source
python main.py analyze "Topic" -s https://rss-feed-url.com

# Use multiple sources
python main.py analyze "Topic" -s source1.com -s source2.com

# View past analysis
python main.py show 20241124_153045_topic_name

# Show configuration
python main.py config
```

## Expected Costs

- **Per analysis (10 articles, 3 sources)**: ~$0.01-0.05 with Haiku
- **100 analyses**: ~$1-5
- Far cheaper than professional media monitoring services!

## Troubleshooting

**"ANTHROPIC_API_KEY not set"**
- Make sure `.env` file exists in project root
- Check that API key is correct and starts with `sk-ant-`

**"No articles fetched"**
- Check internet connection
- Try different sources with `-c international`

**Need help?**
- Check README.md for detailed documentation
- Review logs in `logs/` directory

## Architecture Overview

```
Pipeline Flow:
  RSS Fetcher → Claude Processor → Storage → Markdown Output
       ↓              ↓              ↓            ↓
    Articles      Synthesis      JSON files   .md files

Error handling and logging at every step!
```

## Next Steps

1. ✅ Get basic analysis working (you're here!)
2. Try different source categories
3. Experiment with different topics
4. Review costs in logs
5. Read about Sprint 2+ features in README.md

Happy analyzing! 🚀
