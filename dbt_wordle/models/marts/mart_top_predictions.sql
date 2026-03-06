-- mart_top_predictions
-- Materialization: table
-- Top 10 candidate words most likely to be the next Wordle answer.
-- Excludes words already used as answers.
-- This is the primary output read by the Streamlit dashboard.

with scored as (

    select * from {{ ref('mart_word_scores') }}
    where already_used = false

)

select
    row_number() over (order by total_score desc) as rank,
    word,
    letter_1,
    letter_2,
    letter_3,
    letter_4,
    letter_5,
    total_score,
    pos1_score,
    pos2_score,
    pos3_score,
    pos4_score,
    pos5_score
from scored
qualify rank <= 10
order by rank