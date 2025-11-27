# Sports Load Management Agent

LangGraph-based agent for analyzing athlete training load data. Calculates ACWR (Acute:Chronic Workload Ratio), generates visualizations, and provides AI-powered reports.

## Features

- **Auto Column Detection** - Detects player names, dates, and load data (or RPE × Time)
- **ACWR Calculation** - Short-term (3-day) and long-term (2-week) averages
- **5 Visualizations** - Top players, load distribution, timeline, heatmap
- **AI Reports** - LLM-generated insights and recommendations
- **Downloadable Outputs** - Processed CSV and color-coded Excel files

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
LANGGRAPH_API_ENDPOINT=https://api.openai.com/v1
LANGGRAPH_GENERAL_MODEL=gpt-4
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
3. Click "Analyze Training Load"
4. View results and download files

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload CSV file(s) |
| `/api/process/{session_id}` | POST | Start processing |
| `/api/results/{session_id}` | GET | Get results |
| `/api/download/{session_id}/{filename}` | GET | Download file |

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
│   │   ├── app.py              # FastAPI app
│   │   ├── agent_graph.py      # LangGraph workflow
│   │   ├── core/
│   │   │   ├── load_calculator.py   # ACWR calculations
│   │   │   └── visualizations.py    # Chart generation
│   │   ├── nodes/              # LangGraph nodes
│   │   └── api/routes.py       # API endpoints
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   └── components/
│   └── package.json
└── README.md
```

## License

MIT
