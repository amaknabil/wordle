-- int_position_frequency
-- Materialization: ephemeral (injected as CTE, never stored)
-- Count how often each letter appears in each position (1–5).

with words as (

    select
        letter_1,
        letter_2,
        letter_3,
        letter_4,
        letter_5
    from {{ ref('stg_wordle_words') }}

),

total_words as (

    select count(*) as total from words

),

positioned as (

    select 1 as position, letter_1 as letter from words
    union all
    select 2, letter_2 from words
    union all
    select 3, letter_3 from words
    union all
    select 4, letter_4 from words
    union all
    select 5, letter_5 from words

),

counts as (

    select
        position,
        letter,
        count(*) as position_count
    from positioned
    group by position, letter

)

select
    c.position,
    c.letter,
    c.position_count,
    round(c.position_count * 100.0 / t.total, 4) as position_pct
from counts c
cross join total_words t
order by position, position_count desc