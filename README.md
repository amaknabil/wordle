# 🟩 Wordle Analytics Pipeline

> A full data engineering project that extracts historical Wordle answers, transforms the data through a layered dbt pipeline, and serves letter analysis, difficulty trends, and next-word predictions via an interactive Streamlit dashboard.

---

## 🏗️ Architecture

```
┌──────────────────────┐     ┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  extract_wordle.py   │────▶│   wordle.db      │────▶│   dbt models         │────▶│   dashboard.py      │
│                      │     │   (DuckDB)       │     │   staging            │     │                     │
│  wordlehints.co.uk   │     │                  │     │   intermediate       │     │   Predictions       │
│  API (free, no auth) │     │  raw_wordle_words│     │   marts              │     │   Letter Analysis   │
│                      │     │                  │     │                      │     │   Position Heatmap  │
└──────────────────────┘     └─────────────────┘     └──────────────────────┘     │   History           │
           ▲                                                                        └─────────────────────┘
           │
  pipeline.py — orchestrates all steps daily
```

---

## 🛠️ Stack

| Phase | Tool | Purpose |
|---|---|---|
| Ingestion | Python + `requests` | Fetch Wordle answers from wordlehints API |
| Storage | DuckDB | Local serverless analytical database |
| Transformation | dbt-core + dbt-duckdb | Layered SQL models with lineage & tests |
| Orchestration | `schedule` | Daily pipeline runner |
| Visualization | Streamlit + Plotly | Interactive analytics dashboard |

---

## 📁 Project Structure

```
wordle-analytics/
│
├── 📂 ingestion/
│   └── extract_wordle.py          # Fetches Wordle answers → loads to DuckDB
│
├── 📂 dbt_wordle/                 # dbt project
│   ├── dbt_project.yml
│   ├── profiles.yml               # DuckDB connection (../data/wordle.db)
│   ├── packages.yml
│   │
│   ├── 📂 models/
│   │   ├── 📂 staging/            # view — clean & standardize raw data
│   │   │   ├── schema.yml
│   │   │   └── stg_wordle_words.sql
│   │   │
│   │   ├── 📂 intermediate/       # ephemeral — business logic CTEs
│   │   │   ├── schema.yml
│   │   │   ├── int_letter_frequency.sql
│   │   │   ├── int_position_frequency.sql
│   │   │   └── int_difficulty_by_pattern.sql
│   │   │
│   │   └── 📂 marts/              # table — final outputs for dashboard
│   │       ├── schema.yml
│   │       ├── mart_letter_frequency.sql
│   │       ├── mart_position_heatmap.sql
│   │       ├── mart_answer_history.sql
│   │       ├── mart_word_scores.sql
│   │       └── mart_top_predictions.sql
│   │
│   ├── 📂 seeds/
│   │   └── all_5_letter_words.csv  # Reference list of all valid 5-letter words
│   │
│   └── 📂 tests/
│       └── assert_no_duplicate_answers.sql
│
├── 📂 orchestration/
│   └── pipeline.py                # Runs ingestion + dbt daily
│
├── 📂 visualization/
│   └── dashboard.py               # Streamlit dashboard
│
├── 📂 data/
│   └── wordle.db                  # DuckDB file (auto-created, gitignored)
│
├── .env
├── .gitignore
├── pyproject.toml                 # uv dependency management
└── README.md
```

---

## 🧱 dbt Layer Strategy

```
raw_wordle_words  (loaded by ingestion script)
        │
        ▼
┌─────────────┐  materialized: view
│   staging   │  Clean raw data — uppercase, extract letters 1–5,
└─────────────┘  vowel count, unique letter count, difficulty bucket
        │
        ▼
┌──────────────┐  materialized: ephemeral (CTE, never stored)
│ intermediate │  Letter frequency, positional frequency,
└──────────────┘  difficulty pattern aggregations
        │
        ▼
┌───────────┐      materialized: table (queried by dashboard)
│   marts   │      Word scores, top 10 predictions, answer history,
└───────────┘      letter frequency charts, position heatmap
```

| Layer | Materialization | Reason |
|---|---|---|
| `staging/` | `view` | Always fresh, zero storage cost |
| `intermediate/` | `ephemeral` | Helper logic, never queried directly |
| `marts/` | `table` | Fast reads for dashboard |

---

## 🔮 How Prediction Works

```
1. All valid 5-letter words  (from seeds/all_5_letter_words.csv)
2. Remove already-used Wordle answers
3. Score each remaining word:
      score = Σ (letter_frequency_pct + position_frequency_pct) for each of 5 letters
4. Rank by score descending
5. Top 10 = most likely next answers
```

---

## 📊 Dashboard

Four tabs powered by DuckDB mart tables:

| Tab | Content |
|---|---|
| 🔮 Predictions | Top 10 predicted next words with score bars + per-position breakdown |
| 📊 Letter Analysis | Full letter frequency bar chart + top 10 with visual bars |
| 🔥 Position Heatmap | 26×5 heatmap of letter × position frequency |
| 📅 History | Difficulty over time, distribution pie, vowel counts, recent answers table |

---

## 🚀 Setup

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) installed

### Install

```powershell
git clone https://github.com/amaknabil/wordle.git
cd wordle-analytics
uv sync
```

### Full word list seed
Download the complete 5-letter word list and add a `word` header:

```powershell
# Download
curl https://raw.githubusercontent.com/tabatkins/wordle-list/main/words -o temp.txt

# Add header and save as seed
"word" | Set-Content dbt_wordle\seeds\all_5_letter_words.csv
Get-Content temp.txt | Add-Content dbt_wordle\seeds\all_5_letter_words.csv
Remove-Item temp.txt
```

---

## ▶️ Running

### Run once manually

```powershell
uv run python orchestration/pipeline.py
```

### Run on a daily schedule (08:00)

```powershell
uv run python orchestration/pipeline.py --schedule
```

### Run steps individually

```powershell
# 1. Ingest
uv run python ingestion/extract_wordle.py

# 2. dbt (from inside dbt_wordle/)
cd dbt_wordle
uv run dbt deps
uv run dbt seed --profiles-dir .
uv run dbt run  --profiles-dir .
uv run dbt test --profiles-dir .

# 3. Dashboard
cd ..
uv run streamlit run visualization/dashboard.py
```

---

## 🧪 Data Quality Tests

| Test | What it checks |
|---|---|
| `unique` on `puzzle_number` | No puzzle number appears twice |
| `not_null` on `answer` | Every row has a word |
| `not_null` on `date` | Every row has a date |
| `assert_no_duplicate_answers` | No word used more than twice (NYT repeats answers intentionally since 2024) |

---

## 📝 Notes

- `data/wordle.db` is gitignored — regenerate locally by running the pipeline
- wordlehints API includes a difficulty score (1.0–5.0) not available from NYT directly
- The prediction model is statistical — NYT curates answers manually so results are probabilistic
- dbt models all land in the DuckDB `main` schema alongside raw tables