-- int_difficulty_by_pattern
-- Materialization: ephemeral
-- Aggregate difficulty stats by word pattern groups.
-- Answers without difficulty score (NULL) are excluded.

with words as (

    select
        letter_1,
        vowel_count,
        unique_letter_count,
        difficulty,
        difficulty_bucket
    from {{ ref('stg_wordle_words') }}
    where difficulty is not null

)

select
    vowel_count,
    unique_letter_count,
    difficulty_bucket,
    count(*)                            as word_count,
    round(avg(difficulty), 2)           as avg_difficulty,
    round(min(difficulty), 2)           as min_difficulty,
    round(max(difficulty), 2)           as max_difficulty
from words
group by vowel_count, unique_letter_count, difficulty_bucket
order by avg_difficulty desc