-- mart_answer_history
-- Materialization: table
-- Full enriched history of every Wordle answer.
-- Used by dashboard timeline, difficulty trend, and pattern analysis charts.

with answers as (

    select * from {{ ref('stg_wordle_words') }}

),

letter_freq as (

    select * from {{ ref('int_letter_frequency') }}

)

select
    -- identifiers
    a.puzzle_number,
    a.answer,
    a.answer_date,
    a.day_name,
    a.answer_year,
    a.answer_month,

    -- individual letters
    a.letter_1,
    a.letter_2,
    a.letter_3,
    a.letter_4,
    a.letter_5,

    -- difficulty
    a.difficulty,
    a.difficulty_bucket,

    -- word structure
    a.vowel_count,
    a.unique_letter_count,

    -- how common is each letter in this word
    coalesce(lf1.frequency_pct, 0) as letter_1_freq_pct,
    coalesce(lf2.frequency_pct, 0) as letter_2_freq_pct,
    coalesce(lf3.frequency_pct, 0) as letter_3_freq_pct,
    coalesce(lf4.frequency_pct, 0) as letter_4_freq_pct,
    coalesce(lf5.frequency_pct, 0) as letter_5_freq_pct,

    -- overall word commonality score (sum of all letter frequencies)
    round(
        coalesce(lf1.frequency_pct, 0) +
        coalesce(lf2.frequency_pct, 0) +
        coalesce(lf3.frequency_pct, 0) +
        coalesce(lf4.frequency_pct, 0) +
        coalesce(lf5.frequency_pct, 0), 4
    ) as word_commonality_score

from answers a
left join letter_freq lf1 on lf1.letter = a.letter_1
left join letter_freq lf2 on lf2.letter = a.letter_2
left join letter_freq lf3 on lf3.letter = a.letter_3
left join letter_freq lf4 on lf4.letter = a.letter_4
left join letter_freq lf5 on lf5.letter = a.letter_5
order by a.puzzle_number desc