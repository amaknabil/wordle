-- mart_word_scores
-- Materialization: table
-- Score every valid 5-letter candidate word using:
--   score = sum of (letter_frequency_pct + position_frequency_pct) per letter
-- Words already used as Wordle answers are flagged but kept in this table.
-- Exclusion happens in mart_top_predictions.

with candidates as (

    select upper(word) as word
    from {{ ref('all_5_letter_words') }}

),

used_answers as (

    select answer from {{ ref('stg_wordle_words') }}

),

letter_freq as (

    select * from {{ ref('int_letter_frequency') }}

),

position_freq as (

    select * from {{ ref('int_position_frequency') }}

),

scored as (

    select
        c.word,

        -- individual letters
        substr(c.word, 1, 1) as letter_1,
        substr(c.word, 2, 1) as letter_2,
        substr(c.word, 3, 1) as letter_3,
        substr(c.word, 4, 1) as letter_4,
        substr(c.word, 5, 1) as letter_5,

        -- per-position scores (letter freq + positional freq)
        round(coalesce(lf1.frequency_pct, 0) + coalesce(pf1.position_pct, 0), 4) as pos1_score,
        round(coalesce(lf2.frequency_pct, 0) + coalesce(pf2.position_pct, 0), 4) as pos2_score,
        round(coalesce(lf3.frequency_pct, 0) + coalesce(pf3.position_pct, 0), 4) as pos3_score,
        round(coalesce(lf4.frequency_pct, 0) + coalesce(pf4.position_pct, 0), 4) as pos4_score,
        round(coalesce(lf5.frequency_pct, 0) + coalesce(pf5.position_pct, 0), 4) as pos5_score,

        -- already used as a Wordle answer?
        case
            when c.word in (select answer from used_answers) then true
            else false
        end as already_used

    from candidates c

    -- letter frequency joins
    left join letter_freq lf1 on lf1.letter = substr(c.word, 1, 1)
    left join letter_freq lf2 on lf2.letter = substr(c.word, 2, 1)
    left join letter_freq lf3 on lf3.letter = substr(c.word, 3, 1)
    left join letter_freq lf4 on lf4.letter = substr(c.word, 4, 1)
    left join letter_freq lf5 on lf5.letter = substr(c.word, 5, 1)

    -- positional frequency joins
    left join position_freq pf1 on pf1.letter = substr(c.word, 1, 1) and pf1.position = 1
    left join position_freq pf2 on pf2.letter = substr(c.word, 2, 1) and pf2.position = 2
    left join position_freq pf3 on pf3.letter = substr(c.word, 3, 1) and pf3.position = 3
    left join position_freq pf4 on pf4.letter = substr(c.word, 4, 1) and pf4.position = 4
    left join position_freq pf5 on pf5.letter = substr(c.word, 5, 1) and pf5.position = 5

)

select
    word,
    letter_1,
    letter_2,
    letter_3,
    letter_4,
    letter_5,
    round(pos1_score + pos2_score + pos3_score + pos4_score + pos5_score, 4) as total_score,
    pos1_score,
    pos2_score,
    pos3_score,
    pos4_score,
    pos5_score,
    already_used
from scored
order by total_score desc