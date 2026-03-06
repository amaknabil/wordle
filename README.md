# 🟩 Wordle Analytics Pipeline

> A full data engineering project that extracts historical Wordle answers, transforms the data through a layered dbt pipeline, and serves predictions and insights via an interactive Streamlit dashboard.

---

## 🎯 What This Project Does

1. **Extracts** daily Wordle answers from the web
2. **Loads** raw data into a local DuckDB database
3. **Transforms** it through staging → intermediate → marts using dbt
4. **Predicts** the most likely next Wordle word based on letter and positional frequency
5. **Visualizes** everything in a Streamlit dashboard

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌───────────────────┐
│  extract_       │     │              │     │   dbt models    │     │   Streamlit       │
│  wordle.py      │────▶│  wordle.db   │────▶│   (3 layers)    │────▶│   dashboard.py    │
│  (ingestion)    │     │  (DuckDB)    │     │   (transform)   │     │   (visualization) │
└─────────────────┘     └──────────────┘     └─────────────────┘     └───────────────────┘
        ▲                                              ▲
        │                                              │
   pipeline.py ─────────────────────────────────────────
   (orchestration — runs everything daily)
```

---

## 🛠️ Stack

| Phase | Tool | Why |
|---|---|---|
| Ingestion | Python + `requests` + `beautifulsoup4` | Scrape & parse Wordle pages |
| Storage | DuckDB | Local, serverless, fast analytics SQL |
| Transformation | dbt-core + dbt-duckdb | Layered SQL models with lineage |
| Orchestration | `schedule` | Lightweight daily cron-like runner |
| Visualization | Streamlit + Plotly | Interactive dashboard in pure Python |

---

## 📁 Project Structure

```
wordle-analytics/
│
├── 📂 ingestion/
│   └── extract_wordle.py          # Fetches daily Wordle word → loads to DuckDB
│
├── 📂 dbt_wordle/                 # dbt project root
│   ├── dbt_project.yml            # Materialization config per layer
│   ├── profiles.yml               # DuckDB connection
│   │
│   ├── 📂 models/
│   │   ├── 📂 staging/
│   │   │   └── stg_wordle_words.sql         # Clean & standardize raw data
│   │   │
│   │   ├── 📂 intermediate/
│   │   │   ├── int_letter_frequency.sql     # Letter usage counts
│   │   │   └── int_position_frequency.sql  # Letter frequency per position (1-5)
│   │   │
│   │   └── 📂 marts/
│   │       ├── mart_word_scores.sql         # Score every 5-letter candidate word
│   │       └── mart_top_predictions.sql     # Top 10 predicted next words
│   │
│   ├── 📂 seeds/
│   │   └── all_5_letter_words.csv          # Reference list of valid 5-letter words
│   │
│   └── 📂 tests/
│       └── assert_no_duplicate_words.sql   # Data quality checks
│
├── 📂 orchestration/
│   └── pipeline.py                # Runs ingestion + dbt run + dbt test daily
│
├── 📂 visualization/
│   └── dashboard.py               # Streamlit app — charts + predictions
│
├── 📂 data/
│   └── wordle.db                  # DuckDB database file (auto-created on first run)
│
├── .env                           # Environment config
├── .gitignore
├── pyproject.toml                 # uv dependency management
└── README.md
```

---

## 🧱 dbt Layer Strategy

```
raw_wordle_words  (DuckDB table — loaded by ingestion script)
       │
       ▼
┌─────────────┐   materialized: view
│   staging   │   Light cleaning only — rename columns, cast types, filter nulls
└─────────────┘
       │
       ▼
┌──────────────┐  materialized: ephemeral
│ intermediate │  Business logic — letter counts, position frequency calculations
└──────────────┘
       │
       ▼
┌───────────┐      materialized: table
│   marts   │      Final outputs — word scores, top 10 predictions, ready for dashboard
└───────────┘
```

| Layer | Materialization | Reason |
|---|---|---|
| `staging/` | `view` | Always fresh, zero storage cost |
| `intermediate/` | `ephemeral` | Helper logic injected as CTEs, never stored |
| `marts/` | `table` | Queried heavily by dashboard, needs to be fast |

---

## 🚀 Setup

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) installed
- VS Code with Claude Code extension (optional but recommended)

### Installation

```powershell
# 1. Clone the project
git clone https://github.com/your-username/wordle-analytics.git
cd wordle-analytics

# 2. Install dependencies with uv
uv sync
```

### Running the Pipeline

```powershell
# Step 1 — Load historical Wordle words into DuckDB
uv run python ingestion/extract_wordle.py

# Step 2 — Seed reference word list
cd dbt_wordle
uv run dbt seed

# Step 3 — Run all dbt transformations
uv run dbt run

# Step 4 — Run data quality tests
uv run dbt test

# Step 5 — Launch dashboard
uv run streamlit run visualization/dashboard.py
```

### Run Everything at Once (Daily Pipeline)

```powershell
uv run python orchestration/pipeline.py
```

---

## 📊 Dashboard Features

- 📈 **Letter frequency bar chart** — most common letters in Wordle answers
- 🔥 **Position heatmap** — which letters appear most in each position (1–5)
- 📅 **Answer timeline** — browse all historical answers
- 🔮 **Top 10 predictions** — ranked candidate words for tomorrow's answer

---

## 🔮 How Prediction Works

```
1. Take all valid 5-letter English words (from seeds/all_5_letter_words.csv)
2. Remove words already used as Wordle answers
3. Score each remaining word:
      score = sum of (letter frequency × position frequency) for each of 5 letters
4. Rank by score descending
5. Top 10 = most likely next answers
```

---

## 🧪 Data Quality Tests

| Test | What it checks |
|---|---|
| `assert_no_duplicate_words` | No word appears twice in answer history |
| `not_null` on `answer` | Every row has a word |
| `not_null` on `date` | Every row has a date |
| `unique` on `puzzle_number` | Puzzle numbers are distinct |

---

## 📝 Notes

- DuckDB database (`data/wordle.db`) is excluded from git — regenerate locally by running ingestion
- `profiles.yml` points to `../data/wordle.db` relative to the `dbt_wordle/` folder
- The prediction model is statistical, not guaranteed — NYT curates answers manually