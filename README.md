# Sports Load Management Agent

LangGraph-based agent for analyzing athlete training load data. Calculates ACWR (Acute:Chronic Workload Ratio), generates visualizations, and provides AI-powered interpretation reports.

## Features

- **Automatic Column Detection**: Smart detection of player identifiers, dates, and load data (supports both raw load and RPE × Time for sRPE calculation)
- **Multi-file Support**: Upload and combine multiple CSV files
- **ACWR Calculation**: 
  - Short-term average (3-day rolling)
  - Long-term average (2-week)
  - Load ratio (ACWR = short/long)
  - Load quality categorization (high/medium/low)
- **Visualizations**:
  - Top players by load (bar chart)
  - Load quality distribution (pie chart)
  - Team load timeline
  - Player load heatmap
- **AI-Powered Reports**: LLM-generated insights and recommendations
- **Token Tracking**: Monitor API usage per session

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key (or compatible endpoint)

### Installation

```bash
cd backend

# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### Environment Setup

Create a `.env` file in the `backend` directory:

```env
OPENAI_API_KEY=your-api-key
LANGGRAPH_API_ENDPOINT=https://api.openai.com/v1  # Or your preferred endpoint
LANGGRAPH_GENERAL_MODEL=gpt-4.1  # Or your preferred model
```

### Running the Server

```bash
cd backend

# Development mode
python -m sports_load_agent.app

# Or using uvicorn directly
uvicorn sports_load_agent.app:app --host 0.0.0.0 --port 8000 --reload

# Or using LangGraph dev server
langgraph dev
```

The API will be available at `http://localhost:8000`

## API Usage

### 1. Upload Files

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "files=@training_data.csv"
```

Response:
```json
{
  "session_id": "abc123...",
  "uploaded_files": ["uploads/abc123.../training_data.csv"],
  "message": "Successfully uploaded 1 file(s)"
}
```

### 2. Process Data

```bash
curl -X POST "http://localhost:8000/api/process/{session_id}"
```

### 3. Get Results

```bash
curl "http://localhost:8000/api/results/{session_id}"
```

Response includes:
- `report_markdown`: AI-generated analysis report
- `visualization_files`: URLs to generated charts
- `processed_csv_path`: URL to processed CSV
- `processed_excel_path`: URL to colored Excel file
- `token_usage`: API token statistics

### 4. Download Files

```bash
curl "http://localhost:8000/api/download/{session_id}/{filename}" -o output.png
```

## Data Format

### Input CSV Requirements

Your CSV should include columns for:

1. **Player Identifier** (any of these names):
   - `Athlete Name`, `Player`, `Name`, `player_name`, `Athlete`, `ID`

2. **Date**:
   - `Date`, `date`, `Day`, `Training Date`

3. **Load Data** (one of these options):
   - Direct load: `Load`, `Training Load`, `sRPE`, `Workload`
   - OR separate RPE and Time columns:
     - RPE: `RPE`, `Rating of Perceived Exertion`
     - Time: `Time`, `Time (mins)`, `Duration`, `Minutes`

### Example CSV

```csv
Athlete Name,RPE,Time (mins),Date
John Smith,7,90,2024-01-15
Jane Doe,6,75,2024-01-15
John Smith,8,60,2024-01-16
```

## ACWR Interpretation

| ACWR Range | Category | Meaning |
|------------|----------|---------|
| > 1.5 | High | Elevated injury risk - consider reducing load |
| 0.67 - 1.5 | Medium | Optimal training zone |
| < 0.67 | Low | Potential undertraining - fitness may decline |

## Project Structure

```
sports-load-management-agent/
├── backend/
│   ├── src/sports_load_agent/
│   │   ├── agent_state.py       # State management
│   │   ├── agent_graph.py       # LangGraph workflow
│   │   ├── settings.py          # Configuration
│   │   ├── app.py               # FastAPI app
│   │   ├── nodes/               # LangGraph nodes
│   │   ├── core/                # Business logic
│   │   ├── utils/               # Utilities
│   │   └── api/                 # API routes
│   ├── runtime_cache/           # Cached DataFrames
│   ├── uploads/                 # Uploaded files
│   └── outputs/                 # Generated outputs
└── README.md
```

## Development

### Running Tests

```bash
cd backend
pytest tests/
```

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

MIT
