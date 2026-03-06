-- int_letter_frequency
-- Materialization: ephemeral (injected as CTE, never stored)
-- Count how often each letter appears across all Wordle answers.

with words as (

    select
        answer,
        letter_1,
        letter_2,
        letter_3,
        letter_4,
        letter_5
    from {{ ref('stg_wordle_words') }}

),

-- unpivot each word into individual letters
letters as (

    select letter_1 as letter from words
    union all
    select letter_2 from words
    union all
    select letter_3 from words
    union all
    select letter_4 from words
    union all
    select letter_5 from words

),

counts as (

    select
        letter,
        count(*) as total_count
    from letters
    group by letter

)

select
    letter,
    total_count,
    round(total_count * 100.0 / sum(total_count) over (), 4) as frequency_pct,
    rank() over (order by total_count desc)                  as frequency_rank
from counts
order by total_count desc