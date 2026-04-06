# 🚀 EchoWrite AI — Multi-Agent Content Transformation System

An AI-powered content pipeline that **scrapes web content**, transforms it through **specialized AI agents** working collaboratively, learns from **human feedback via reinforcement learning**, and supports **semantic search** and **voice interaction**.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI (app.py)                    │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ │
│  │ Process  │ │Analytics │ │Training│ │ Search │ │ Settings │ │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └───┬────┘ └──────────┘ │
└───────┼────────────┼───────────┼──────────┼─────────────────────┘
        │            │           │          │
   ┌────▼────┐  ┌────▼────┐  ┌──▼───┐  ┌──▼──────────┐
   │ Scraper │  │ Version │  │Reward│  │  ChromaDB   │
   │(Playwright│ │ Manager │  │Model │  │Semantic Sear│
   │  + BS4)  │  │ (JSON)  │  │(RLHF)│  │   (Vector)  │
   └────┬─────┘  └─────────┘  └──┬───┘  └─────────────┘
        │                         │
   ┌────▼─────────────────────────▼──────────────────────┐
   │              Multi-Agent Pipeline                    │
   │  ┌────────┐    ┌──────────┐    ┌────────┐          │
   │  │ Writer │───▶│ Reviewer │───▶│ Editor │──┐       │
   │  │ Agent  │    │  Agent   │    │ Agent  │  │       │
   │  └────────┘    └──────────┘    └────────┘  │       │
   │       ▲                                     │       │
   │       └─────── iterate ◀────────────────────┘       │
   └─────────────────────────────────────────────────────┘
        │                         │
   ┌────▼─────┐          ┌───────▼────────┐
   │  Gemini  │          │ Inference Eng. │
   │   API    │          │ (ε-greedy RL)  │
   └──────────┘          └────────────────┘
```

## Key Components

### 1. Web Scraping (`scrapers/`)
- **SyncWebScraper** — `requests` + BeautifulSoup with multi-method screenshot fallback (Playwright → Selenium → Pyppeteer → HTML save)
- **WebContentScraper** — Async Playwright-based scraper for full browser rendering

### 2. AI Agents (`agents/`)
- **WriterAgent** — Rewrites raw content in a target style (engaging, professional, casual, academic, creative)
- **ReviewerAgent** — Scores content on quality, clarity, engagement, accuracy (1-10) and suggests improvements
- **EditorAgent** — Applies reviewer + human feedback to refine content
- **VoiceInterface** — STT (Google) + TTS (gTTS/pyttsx3/SAPI) with command parsing
- **Voice-Enabled Agents** — Wrappers that announce progress via voice

### 3. Storage (`storage/`)
- **VersionManager** — JSON file-based versioning with full original/rewritten text, metadata, and history

### 4. RL Models (`rl_models/`)
- **RewardModel** — Learns from human ratings per style; predicts quality; blends AI + human rewards (0.7/0.3 weighting)
- **ContentSelectionEngine** — Generates N style variants, scores via ReviewerAgent, selects best with ε-greedy exploration

### 5. Semantic Search (`search/`)
- **SemanticSearch** — ChromaDB persistent vector store; indexes original + rewritten content; supports style/URL filtering and cosine similarity search

---

## Setup

```bash
# 1. Clone & enter
cd echowrite

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Set your API key
cp .env.example .env
# Edit .env → add your GEMINI_API_KEY

# 6. Run
streamlit run app.py
```

## Usage

### Process Tab
1. Enter a URL (default: Wikisource chapter)
2. Select writing style
3. Set max AI iterations (1-5)
4. Optionally enable **RL Inference** for multi-version generation
5. Click **Process Content**
6. Review side-by-side comparison + score charts
7. Provide human-in-the-loop feedback inline

### Training Tab
- Rate any past version on a 0-1 scale
- The reward model updates immediately
- View AI-recommended optimal parameters

### Search Tab
- Query indexed content by meaning
- Filter by style
- Results ranked by cosine similarity

### Analytics Tab
- Quality trends over time
- Style distribution pie chart
- Per-style average ratings from human feedback

---

## Project Structure

```
echowrite/
├── config/
│   ├── __init__.py
│   └── settings.py          # Dataclass config + env vars
├── scrapers/
│   ├── __init__.py
│   ├── sync_scraper.py       # Sync BS4 + screenshot chain
│   └── web_scraper.py        # Async Playwright scraper
├── agents/
│   ├── __init__.py
│   ├── writer.py             # Gemini-powered rewriter
│   ├── reviewer_agent.py     # Structured JSON scorer
│   ├── editor_agent.py       # Feedback-driven improver
│   ├── voice_interface.py    # STT/TTS + command parser
│   └── voice_enabled_agents.py
├── storage/
│   ├── __init__.py
│   └── version_manager.py    # JSON file versioning
├── rl_models/
│   ├── __init__.py
│   ├── reward_model.py       # RLHF reward + prediction
│   └── inference_engine.py   # ε-greedy content selection
├── search/
│   ├── __init__.py
│   └── semantic_search.py    # ChromaDB vector search
├── app.py                    # Streamlit UI
├── requirements.txt
├── .env.example
└── README.md
```

---

## How the RL Loop Works

1. **Generate** — The inference engine creates N content variants in different styles
2. **Score** — Each variant is reviewed by the AI ReviewerAgent
3. **Select** — ε-greedy picks the best (or explores a random one)
4. **Human rates** — The user provides a 0-1 quality rating
5. **Learn** — The reward model updates its style preference weights
6. **Predict** — Next time, the model favours styles/iterations that scored highest

The blended reward formula:
```
reward = 0.7 × human_rating + 0.3 × (avg_ai_score / 10)
```

---

## Voice Commands

| Command | Intent |
|---|---|
| "Process https://… in professional style" | Scrape + rewrite |
| "Search for mountain sunrise" | Semantic search |
| "Rate this 8 out of 10" | Submit feedback |
| "What's the status?" | System status |
| "Help" | List commands |
