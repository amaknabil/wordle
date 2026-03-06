"""
dashboard.py
------------
Streamlit dashboard for the Wordle Analytics Pipeline.

Reads directly from DuckDB mart tables:
  - mart_top_predictions   → prediction cards
  - mart_letter_frequency  → letter frequency bar chart
  - mart_position_heatmap  → position heatmap
  - mart_answer_history    → timeline + difficulty trend
"""

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent / "data" / "wordle.db"

st.set_page_config(
    page_title="Wordle Analytics",
    page_icon="🟩",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

    :root {
        --green:  #6aaa64;
        --yellow: #c9b458;
        --gray:   #787c7e;
        --dark:   #121213;
        --tile:   #1a1a1b;
        --border: #3a3a3c;
        --text:   #ffffff;
        --muted:  #818384;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        background-color: var(--dark);
        color: var(--text);
    }

    .main { background-color: var(--dark); }
    .block-container { padding: 2rem 3rem; max-width: 1400px; }

    /* Header */
    .wordle-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 2rem;
    }
    .wordle-header h1 {
        font-family: 'Space Mono', monospace;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        color: var(--text);
        margin: 0;
    }
    .wordle-header p {
        color: var(--muted);
        font-size: 0.95rem;
        margin-top: 0.5rem;
        font-weight: 300;
        letter-spacing: 0.05em;
    }

    /* Wordle tile grid */
    .tile-row {
        display: flex;
        gap: 6px;
        justify-content: center;
        margin: 0.3rem 0;
    }
    .tile {
        width: 52px;
        height: 52px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Space Mono', monospace;
        font-size: 1.4rem;
        font-weight: 700;
        border: 2px solid var(--border);
        border-radius: 4px;
        background: var(--tile);
        color: var(--text);
        letter-spacing: 0;
    }
    .tile.green  { background: var(--green);  border-color: var(--green);  }
    .tile.yellow { background: var(--yellow); border-color: var(--yellow); }
    .tile.gray   { background: var(--gray);   border-color: var(--gray);   }

    /* Prediction cards */
    .pred-card {
        background: var(--tile);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .pred-rank {
        font-family: 'Space Mono', monospace;
        font-size: 0.75rem;
        color: var(--muted);
        min-width: 24px;
    }
    .pred-word {
        font-family: 'Space Mono', monospace;
        font-size: 1.3rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        color: var(--text);
        flex: 1;
    }
    .pred-score {
        font-family: 'Space Mono', monospace;
        font-size: 0.75rem;
        color: var(--green);
    }

    /* Score bar */
    .score-bar-container {
        flex: 2;
        background: var(--border);
        border-radius: 2px;
        height: 4px;
        overflow: hidden;
    }
    .score-bar {
        height: 100%;
        background: linear-gradient(90deg, var(--green), var(--yellow));
        border-radius: 2px;
    }

    /* Metric cards */
    .metric-card {
        background: var(--tile);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-value {
        font-family: 'Space Mono', monospace;
        font-size: 2rem;
        font-weight: 700;
        color: var(--green);
    }
    .metric-label {
        font-size: 0.8rem;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 0.3rem;
    }

    /* Section headers */
    .section-title {
        font-family: 'Space Mono', monospace;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        color: var(--muted);
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.5rem;
        margin-bottom: 1.2rem;
    }

    /* Streamlit overrides */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--tile);
        border-radius: 8px;
        gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Space Mono', monospace;
        font-size: 0.8rem;
        letter-spacing: 0.1em;
        color: var(--muted);
        padding: 0.6rem 1.5rem;
    }
    .stTabs [aria-selected="true"] {
        color: var(--text) !important;
        background: var(--border) !important;
        border-radius: 6px;
    }
    div[data-testid="stMetricValue"] {
        font-family: 'Space Mono', monospace;
        color: var(--green);
    }
    .stDataFrame { border: 1px solid var(--border); border-radius: 8px; }

    /* Hide streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=300)
def load_predictions() -> pd.DataFrame:
    con = get_connection()
    return con.execute("""
        SELECT rank, word, letter_1, letter_2, letter_3, letter_4, letter_5,
               total_score, pos1_score, pos2_score, pos3_score, pos4_score, pos5_score
        FROM mart_top_predictions
        ORDER BY rank
    """).df()


@st.cache_data(ttl=300)
def load_letter_frequency() -> pd.DataFrame:
    con = get_connection()
    return con.execute("""
        SELECT letter, total_count, frequency_pct, frequency_rank
        FROM mart_letter_frequency
        ORDER BY total_count DESC
    """).df()


@st.cache_data(ttl=300)
def load_position_heatmap() -> pd.DataFrame:
    con = get_connection()
    return con.execute("""
        SELECT position, letter, position_count, position_pct
        FROM mart_position_heatmap
        ORDER BY position, position_count DESC
    """).df()


@st.cache_data(ttl=300)
def load_answer_history() -> pd.DataFrame:
    con = get_connection()
    return con.execute("""
        SELECT puzzle_number, answer, answer_date, day_name,
               answer_year, answer_month,
               difficulty, difficulty_bucket,
               vowel_count, unique_letter_count,
               word_commonality_score
        FROM mart_answer_history
        ORDER BY puzzle_number DESC
    """).df()


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Space Mono, monospace", color="#ffffff"),
    margin=dict(l=10, r=10, t=30, b=10),
)
AXIS_STYLE = dict(gridcolor="#3a3a3c", zerolinecolor="#3a3a3c")


def tile_html(letters: list[str], colors: list[str] = None) -> str:
    """Render a Wordle-style tile row."""
    if colors is None:
        colors = [""] * len(letters)
    tiles = "".join(
        f'<div class="tile {c}">{l}</div>'
        for l, c in zip(letters, colors)
    )
    return f'<div class="tile-row">{tiles}</div>'


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="wordle-header">
    <h1>🟩 WORDLE ANALYTICS</h1>
    <p>Letter frequency · Positional analysis · Next word predictions</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

try:
    df_pred    = load_predictions()
    df_letters = load_letter_frequency()
    df_heatmap = load_position_heatmap()
    df_history = load_answer_history()
except Exception as e:
    st.error(f"Could not connect to database: {e}")
    st.info("Make sure you have run the pipeline first: `uv run python orchestration/pipeline.py`")
    st.stop()

# ---------------------------------------------------------------------------
# Top metrics row
# ---------------------------------------------------------------------------

total_puzzles  = len(df_history)
avg_difficulty = df_history["difficulty"].mean()
avg_vowels     = df_history["vowel_count"].mean()
latest_puzzle  = df_history["puzzle_number"].max()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{total_puzzles:,}</div>
        <div class="metric-label">Total Puzzles</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">#{latest_puzzle}</div>
        <div class="metric-label">Latest Puzzle</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{avg_difficulty:.2f}</div>
        <div class="metric-label">Avg Difficulty</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{avg_vowels:.1f}</div>
        <div class="metric-label">Avg Vowels / Word</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs([
    "🔮  PREDICTIONS",
    "📊  LETTER ANALYSIS",
    "🔥  POSITION HEATMAP",
    "📅  HISTORY",
])

# ── Tab 1: Predictions ──────────────────────────────────────────────────────

with tab1:
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown('<div class="section-title">Top 10 Predicted Next Words</div>', unsafe_allow_html=True)

        if df_pred.empty:
            st.warning("No predictions available. Run the pipeline first.")
        else:
            max_score = df_pred["total_score"].max()

            for _, row in df_pred.iterrows():
                pct = (row["total_score"] / max_score * 100) if max_score > 0 else 0
                letters = [row["letter_1"], row["letter_2"], row["letter_3"], row["letter_4"], row["letter_5"]]

                st.markdown(f"""
                <div class="pred-card">
                    <div class="pred-rank">#{int(row['rank'])}</div>
                    <div class="pred-word">{''.join(letters)}</div>
                    <div class="score-bar-container">
                        <div class="score-bar" style="width:{pct:.1f}%"></div>
                    </div>
                    <div class="pred-score">{row['total_score']:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-title">Score Breakdown — Top Word</div>', unsafe_allow_html=True)

        if not df_pred.empty:
            top = df_pred.iloc[0]
            letters = [top["letter_1"], top["letter_2"], top["letter_3"], top["letter_4"], top["letter_5"]]
            scores  = [top["pos1_score"], top["pos2_score"], top["pos3_score"], top["pos4_score"], top["pos5_score"]]

            # Tile display
            st.markdown(tile_html(letters), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # Per-position score bar chart
            fig = go.Figure(go.Bar(
                x=[f"Pos {i+1} ({l})" for i, l in enumerate(letters)],
                y=scores,
                marker_color=["#6aaa64", "#6aaa64", "#c9b458", "#6aaa64", "#6aaa64"],
                text=[f"{s:.2f}" for s in scores],
                textposition="outside",
                textfont=dict(family="Space Mono", size=11),
            ))
            fig.update_layout(
                **PLOTLY_LAYOUT,
                xaxis=AXIS_STYLE,
                yaxis={**AXIS_STYLE, "title": "Score"},
                title=dict(text=f"Position scores for {top['word']}", font=dict(size=13)),
                showlegend=False,
                height=320,
            )
            st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: Letter Analysis ───────────────────────────────────────────────────

with tab2:
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown('<div class="section-title">Letter Frequency — All Answers</div>', unsafe_allow_html=True)

        fig = go.Figure(go.Bar(
            x=df_letters["letter"],
            y=df_letters["total_count"],
            marker=dict(
                color=df_letters["total_count"],
                colorscale=[[0, "#3a3a3c"], [0.5, "#c9b458"], [1, "#6aaa64"]],
                showscale=False,
            ),
            text=df_letters["total_count"],
            textposition="outside",
            textfont=dict(family="Space Mono", size=10),
        ))
        fig.update_layout(
            **PLOTLY_LAYOUT,
            xaxis_title="Letter",
            yaxis_title="Count",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-title">Top 10 Letters</div>', unsafe_allow_html=True)

        top10 = df_letters.head(10).copy()
        top10["bar"] = top10["frequency_pct"].apply(
            lambda p: f"{'█' * int(p * 2)} {p:.1f}%"
        )
        for _, row in top10.iterrows():
            pct_bar = int(row["frequency_pct"] * 2)
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <div style="font-family:'Space Mono',monospace; font-size:1.1rem;
                            font-weight:700; color:#6aaa64; min-width:20px;">{row['letter']}</div>
                <div style="flex:1; background:#3a3a3c; border-radius:2px; height:8px; overflow:hidden;">
                    <div style="width:{min(pct_bar * 5, 100)}%; height:100%;
                                background:linear-gradient(90deg,#6aaa64,#c9b458);"></div>
                </div>
                <div style="font-family:'Space Mono',monospace; font-size:0.75rem;
                            color:#818384; min-width:45px;">{row['frequency_pct']:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

# ── Tab 3: Position Heatmap ──────────────────────────────────────────────────

with tab3:
    st.markdown('<div class="section-title">Letter Frequency by Position (1–5)</div>', unsafe_allow_html=True)

    # Pivot for heatmap
    pivot = df_heatmap.pivot_table(
        index="letter", columns="position", values="position_pct", fill_value=0
    )
    pivot.columns = [f"Position {c}" for c in pivot.columns]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[
            [0.0,  "#1a1a1b"],
            [0.3,  "#3a3a3c"],
            [0.6,  "#c9b458"],
            [1.0,  "#6aaa64"],
        ],
        text=[[f"{v:.1f}%" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont=dict(family="Space Mono", size=9),
        hoverongaps=False,
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=700,
        xaxis=dict(side="top", **AXIS_STYLE),
        yaxis=dict(autorange="reversed", **AXIS_STYLE),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Top letter per position
    st.markdown('<div class="section-title">Strongest Letter per Position</div>', unsafe_allow_html=True)

    cols = st.columns(5)
    for pos in range(1, 6):
        pos_data = df_heatmap[df_heatmap["position"] == pos].sort_values("position_pct", ascending=False)
        if not pos_data.empty:
            top_letter = pos_data.iloc[0]
            with cols[pos - 1]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{top_letter['letter']}</div>
                    <div class="metric-label">Position {pos}<br>{top_letter['position_pct']:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

# ── Tab 4: History ───────────────────────────────────────────────────────────

with tab4:
    col_left, col_right = st.columns([2, 1], gap="large")

    with col_left:
        st.markdown('<div class="section-title">Difficulty Over Time</div>', unsafe_allow_html=True)

        df_diff = df_history.dropna(subset=["difficulty"]).sort_values("puzzle_number")

        if not df_diff.empty:
            # Rolling average
            df_diff = df_diff.copy()
            df_diff["rolling_avg"] = df_diff["difficulty"].rolling(30, min_periods=1).mean()

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_diff["puzzle_number"],
                y=df_diff["difficulty"],
                mode="markers",
                marker=dict(color="#3a3a3c", size=3),
                name="Daily",
                showlegend=True,
            ))
            fig.add_trace(go.Scatter(
                x=df_diff["puzzle_number"],
                y=df_diff["rolling_avg"],
                mode="lines",
                line=dict(color="#6aaa64", width=2),
                name="30-day avg",
                showlegend=True,
            ))
            fig.update_layout(
                **PLOTLY_LAYOUT,
                height=350,
                yaxis_title="Difficulty",
                xaxis_title="Puzzle #",
                legend=dict(
                    font=dict(family="Space Mono", size=10),
                    bgcolor="rgba(0,0,0,0)",
                ),
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-title">Difficulty Distribution</div>', unsafe_allow_html=True)

        diff_counts = df_history["difficulty_bucket"].value_counts()
        colors_map  = {"easy": "#6aaa64", "medium": "#c9b458", "hard": "#787c7e"}

        fig = go.Figure(go.Pie(
            labels=diff_counts.index.tolist(),
            values=diff_counts.values.tolist(),
            marker=dict(colors=[colors_map.get(l, "#3a3a3c") for l in diff_counts.index]),
            hole=0.6,
            textfont=dict(family="Space Mono", size=11),
            textinfo="label+percent",
        ))
        fig.update_layout(
            **PLOTLY_LAYOUT,
            height=280,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Vowel count distribution
    st.markdown('<div class="section-title">Vowel Count Distribution</div>', unsafe_allow_html=True)

    vowel_counts = df_history["vowel_count"].value_counts().sort_index()
    fig = go.Figure(go.Bar(
        x=[f"{v} vowel{'s' if v != 1 else ''}" for v in vowel_counts.index],
        y=vowel_counts.values,
        marker_color=["#3a3a3c", "#c9b458", "#6aaa64", "#6aaa64", "#c9b458"],
        text=vowel_counts.values,
        textposition="outside",
        textfont=dict(family="Space Mono", size=11),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=280,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Recent answers table
    st.markdown('<div class="section-title">Recent Answers</div>', unsafe_allow_html=True)

    recent = df_history.head(20)[[
        "puzzle_number", "answer", "answer_date",
        "day_name", "difficulty", "difficulty_bucket",
        "vowel_count", "unique_letter_count"
    ]].rename(columns={
        "puzzle_number":    "Puzzle #",
        "answer":           "Answer",
        "answer_date":      "Date",
        "day_name":         "Day",
        "difficulty":       "Difficulty",
        "difficulty_bucket":"Level",
        "vowel_count":      "Vowels",
        "unique_letter_count": "Unique Letters",
    })

    st.dataframe(
        recent,
        use_container_width=True,
        hide_index=True,
    )