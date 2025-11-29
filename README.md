# Sports Load Management Agent

LangGraph-based agent for analyzing athlete training load data. Calculates ACWR (Acute:Chronic Workload Ratio) and provides conversational AI analysis with tool calling.

## Features

- **Auto Column Detection** - Detects player names, dates, and load data (or RPE × Time)
- **ACWR Calculation** - Short-term (3-day) and long-term (2-week) averages
- **Conversational AI** - Chat with Claude Sonnet 4.5 to analyze your data
- **15 Analysis Tools** - Data queries, visualizations, and custom Python analysis
- **Downloadable Outputs** - Processed CSV and color-coded Excel files

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
├─────────────────────────────────────────────────────────────────┤
│  Upload CSV  →  Process Data  →  Chat with AI Analysis Agent    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Data Ingest  │ → │  Data Process   │ → │   Chat Agent    │
│  (LangGraph)  │   │  (LangGraph)    │   │ (LLM + Tools)   │
└───────────────┘   └─────────────────┘   └─────────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
   Column Mapping      ACWR Calculation      15 Analysis Tools
                       CSV/Excel Export      
```

## Quick Start

### 1. Install Backend

```bash
cd backend
pip install -e .
```

Or with uv:
```bash
cd backend
uv sync
```

### 2. Set Environment Variables

Create `backend/.env`:
```env
OPENAI_API_KEY=your-api-key
LANGGRAPH_API_ENDPOINT=your-endpoint
LANGGRAPH_GENERAL_MODEL=your-choice-of-general-model
LANGGRAPH_CHAT_MODEL=your-choice-of-chat-model
```

### 3. Start Backend

```bash
cd backend
uvicorn sports_load_agent.app:app --host 0.0.0.0 --port 8000
```

Backend runs at: http://localhost:8000  
API docs at: http://localhost:8000/docs

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

### 5. Use the App

1. Open http://localhost:5173
2. Upload your CSV file
3. Download processed data (CSV/Excel with ACWR)
4. Chat with the AI to analyze your data


## Data Format

Your CSV should have columns for:

| Column Type | Accepted Names |
|-------------|----------------|
| Player | `Athlete Name`, `Player`, `Name`, `player_name` |
| Date | `Date`, `date`, `Day` |
| Load | `Load`, `Training Load` OR (`RPE` + `Time`) |

**Example:**
```csv
Athlete Name,RPE,Time (mins),Date
John Smith,7,90,2024-01-15
Jane Doe,6,75,2024-01-15
```

If RPE and Time columns exist, training load is calculated as `RPE × Time`.

## Output Columns

| Column | Description |
|--------|-------------|
| `player_name` | Player identifier |
| `date` | Training date |
| `data` | Raw training load (sRPE) |
| `short_term_ave` | 3-day rolling average |
| `long_term_ave` | 2-week average |
| `ACWR` | Acute:Chronic Workload Ratio |
| `ACWR_category` | high / medium / low |

## ACWR Interpretation

| ACWR | Category | Meaning |
|------|----------|---------|
| > 1.5 | 🔴 High | Injury risk - reduce load |
| 0.67 - 1.5 | 🟡 Medium | Optimal training zone |
| < 0.67 | 🟢 Low | Undertraining risk |

## Project Structure

```
sports-load-management-agent/
├── backend/
│   ├── src/sports_load_agent/
│   │   ├── app.py                 # FastAPI application
│   │   ├── settings.py            # Configuration
│   │   ├── agent_graph.py         # LangGraph workflow (ingest → process)
│   │   ├── agent_state.py         # State schema & DataFrame handling
│   │   ├── chat_agent.py          # Conversational AI agent
│   │   ├── api/
│   │   │   └── routes.py          # API endpoints
│   │   ├── core/
│   │   │   ├── load_calculator.py # ACWR calculations
│   │   │   └── visualizations.py  # Chart generation functions
│   │   ├── nodes/
│   │   │   ├── data_ingest_node.py   # CSV loading + column mapping
│   │   │   └── data_process_node.py  # ACWR calculation + export
│   │   ├── tools/
│   │   │   ├── data_query_tools.py   # 8 data query tools
│   │   │   ├── visualization_tools.py # 6 visualization tools
│   │   │   └── python_sandbox.py     # Sandboxed Python execution
│   │   └── utils/
│   │       ├── column_mapper.py   # LLM-based column detection
│   │       └── llm_factory.py     # LLM initialization + token tracking
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # Main app with chat integration
│   │   ├── api/client.ts          # API client
│   │   ├── components/
│   │   │   ├── Chat.tsx           # Chat interface
│   │   │   ├── FileUpload.tsx     # File upload component
│   │   │   └── ProcessingStatus.tsx
│   │   └── hooks/
│   │       ├── useProcessing.ts   # Processing state management
│   │       └── useChat.ts         # Chat state management
│   └── package.json
└── README.md
```


## License

MIT
