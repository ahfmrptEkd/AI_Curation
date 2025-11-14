# Claude Desktop MCP Integration Setup Guide

This guide will help you configure Claude Desktop to use the Book Curator MCP server.

## Prerequisites

✅ Claude Desktop installed
✅ FastMCP installed (`pip install fastmcp`)
✅ All project dependencies installed
✅ `.env` file configured with API keys

## Step 1: Locate Claude Desktop Config File

### macOS
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

### Windows
```bash
%APPDATA%\Claude\claude_desktop_config.json
```

### Linux
```bash
~/.config/Claude/claude_desktop_config.json
```

## Step 2: Get Absolute Paths

Run these commands in your terminal:

```bash
# Project root path
cd /home/sam/projects/AI_Curation && pwd
# Output: /home/sam/projects/AI_Curation

# Python executable path (from venv)
which python
# Or: /home/sam/projects/AI_Curation/.venv/bin/python
```

## Step 3: Edit claude_desktop_config.json

Open the config file and add this configuration:

```json
{
  "mcpServers": {
    "book-curator": {
      "command": "/home/sam/projects/AI_Curation/.venv/bin/python",
      "args": [
        "/home/sam/projects/AI_Curation/src/mcp/server.py"
      ],
      "env": {
        "PYTHONPATH": "/home/sam/projects/AI_Curation",
        "OPENAI_API_KEY": "your-openai-api-key-here",
        "GOOGLE_SHEETS_ID": "your-google-sheets-id-here",
        "GOOGLE_CREDENTIALS_PATH": "/home/sam/projects/AI_Curation/credentials.json"
      }
    }
  }
}
```

**IMPORTANT**: Replace the following:
- `your-openai-api-key-here` → Your actual OpenAI API key (from `.env`)
- `your-google-sheets-id-here` → Your Google Sheets ID (from `.env`)
- Update paths if your project is in a different location

**Alternative**: Load from `.env` file automatically (if supported by your MCP version):
```json
{
  "mcpServers": {
    "book-curator": {
      "command": "/home/sam/projects/AI_Curation/.venv/bin/python",
      "args": [
        "/home/sam/projects/AI_Curation/src/mcp/server.py"
      ],
      "cwd": "/home/sam/projects/AI_Curation"
    }
  }
}
```

## Step 4: Restart Claude Desktop

1. **Quit Claude Desktop completely** (don't just close the window)
   - macOS: `Cmd+Q`
   - Windows: Right-click system tray icon → Quit
   - Linux: `killall Claude` or close from system tray

2. **Start Claude Desktop again**

3. **Check for MCP icon** in the chat interface (hammer or tools icon)

## Step 5: Verify Installation

In Claude Desktop, type:

```
Can you check what MCP tools are available?
```

You should see:
- ✅ `recommend_books` - Get Romance book recommendations
- ✅ `add_book_review` - Add a new book review

## Step 6: Test the Tools

### Test 1: Book Recommendations
```
Can you recommend some Dark Romance books with rating 4.0 or higher?
```

Expected: Claude will use `recommend_books` tool and show you 3 book recommendations with explanations.

### Test 2: Add a Review
```
Add a review for "Icebreaker" by Hannah Grace, rated 4.5 stars,
category "Sports Romance", review: "Amazing sports romance with great chemistry!"
```

Expected: Claude will use `add_book_review` tool and confirm the review was added with generated emotion tags.

## Troubleshooting

### Issue: Claude Desktop doesn't show MCP tools

**Solution 1**: Check config file location
```bash
# macOS
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Linux
ls -la ~/.config/Claude/claude_desktop_config.json
```

**Solution 2**: Verify JSON syntax
```bash
# Use a JSON validator or:
python -m json.tool ~/.config/Claude/claude_desktop_config.json
```

**Solution 3**: Check logs
```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp*.log

# Linux
tail -f ~/.config/Claude/logs/mcp*.log
```

### Issue: MCP server fails to start

**Test server manually**:
```bash
cd /home/sam/projects/AI_Curation
source .venv/bin/activate
python src/mcp/server.py
```

Expected output:
```
============================================================
📚 Book Curator MCP Server
============================================================

Starting server...
This server provides Romance book recommendations via MCP.

Available tools:
  1. recommend_books - Get personalized recommendations
  2. add_book_review - Add a new book review

Server is ready for connections from Claude Desktop.
============================================================
```

If this works but Claude Desktop doesn't connect:
1. Check that paths in config are **absolute** (not relative)
2. Verify Python path: `which python` (use venv python)
3. Ensure `.env` file exists or env vars are set in config

### Issue: "Module not found" errors

**Solution**: Add project root to PYTHONPATH in config:
```json
"env": {
  "PYTHONPATH": "/home/sam/projects/AI_Curation"
}
```

### Issue: API key errors

**Solution**: Verify environment variables are set correctly:
```bash
# Check .env file
cat .env | grep OPENAI_API_KEY
cat .env | grep GOOGLE_SHEETS_ID

# Or set directly in config (see Step 3)
```

## Available Tools Documentation

### 1. recommend_books

**Purpose**: Get personalized Romance book recommendations

**Parameters**:
- `query` (required): Natural language query (e.g., "dark romance with enemies to lovers")
- `category` (optional): Romance subgenre filter (e.g., "Dark Romance", "Sports Romance")
- `min_rating` (optional): Minimum rating 1.0-5.0 (e.g., 4.0)
- `count` (optional): Number of recommendations (default: 3, max: 10)

**Examples**:
```
"Recommend me some Dark Romance books"
"Find Sports Romance books with rating above 4.0"
"Give me 5 enemies to lovers romance recommendations"
```

**Returns**:
- List of books with title, author, rating, tags, description
- AI-generated explanation for why each book was recommended
- Similarity scores

### 2. add_book_review

**Purpose**: Add a new book review to the system

**Parameters**:
- `title` (required): Book title
- `author` (required): Author name
- `rating` (required): Rating 1.0-5.0
- `review` (required): Your review text
- `category` (required): Book category/trope

**Examples**:
```
"Add a review for Icebreaker by Hannah Grace, 4.5 stars, Sports Romance,
 review: Amazing chemistry between the leads!"
```

**Returns**:
- Confirmation of review addition
- Auto-generated emotion tags
- Vector DB update confirmation

## Notes

- **Language Support**: Reviews and queries work in both English and Korean
- **Database**: Recommendations come from 438 books (252 read + 186 discovered)
- **Filtering**: Only recommends from 'discovered' books (not your reading history)
- **Performance**: First query may be slow (initializes components), subsequent queries are faster

## Support

For issues or questions:
1. Check [claude.md](claude.md) for project documentation
2. Review [scripts/04_test_recommendation.py](scripts/04_test_recommendation.py) for examples
3. Test MCP server manually (see Troubleshooting section)

---

**Last Updated**: 2025-11-03
**MCP Version**: FastMCP 2.13.0.2
**Project**: AI_Curation Book Recommendation System
