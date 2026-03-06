-- stg_wordle_words
-- Materialization: view
-- Clean and standardize raw Wordle answers.
-- One row per puzzle. This is the single source of truth for all downstream models.

with source as (

    select * from {{ source('raw', 'raw_wordle_words') }}

),

cleaned as (

    select
        -- identifiers
        cast(puzzle_number as integer)                  as puzzle_number,

        -- answer — always uppercase, trimmed
        upper(trim(answer))                             as answer,

        -- individual letters for frequency analysis
        substr(upper(trim(answer)), 1, 1)               as letter_1,
        substr(upper(trim(answer)), 2, 1)               as letter_2,
        substr(upper(trim(answer)), 3, 1)               as letter_3,
        substr(upper(trim(answer)), 4, 1)               as letter_4,
        substr(upper(trim(answer)), 5, 1)               as letter_5,

        -- dates
        cast(date as date)                              as answer_date,
        day_name,
        extract('year'  from cast(date as date))        as answer_year,
        extract('month' from cast(date as date))        as answer_month,

        -- difficulty (1.0 = easy, 5.0 = hard)
        difficulty,

        -- derived flags
        case
            when difficulty >= 4.0 then 'hard'
            when difficulty >= 3.0 then 'medium'
            else 'easy'
        end                                             as difficulty_bucket,

        -- vowel count
        (
            case when substr(upper(trim(answer)), 1, 1) in ('A','E','I','O','U') then 1 else 0 end +
            case when substr(upper(trim(answer)), 2, 1) in ('A','E','I','O','U') then 1 else 0 end +
            case when substr(upper(trim(answer)), 3, 1) in ('A','E','I','O','U') then 1 else 0 end +
            case when substr(upper(trim(answer)), 4, 1) in ('A','E','I','O','U') then 1 else 0 end +
            case when substr(upper(trim(answer)), 5, 1) in ('A','E','I','O','U') then 1 else 0 end
        )                                               as vowel_count,

        -- unique letter count (1 = all 5 letters distinct, <5 = has repeats)
        (
            case when substr(upper(trim(answer)), 1, 1)
                 not in (substr(upper(trim(answer)), 2, 1),
                         substr(upper(trim(answer)), 3, 1),
                         substr(upper(trim(answer)), 4, 1),
                         substr(upper(trim(answer)), 5, 1)) then 1 else 0 end +
            case when substr(upper(trim(answer)), 2, 1)
                 not in (substr(upper(trim(answer)), 1, 1),
                         substr(upper(trim(answer)), 3, 1),
                         substr(upper(trim(answer)), 4, 1),
                         substr(upper(trim(answer)), 5, 1)) then 1 else 0 end +
            case when substr(upper(trim(answer)), 3, 1)
                 not in (substr(upper(trim(answer)), 1, 1),
                         substr(upper(trim(answer)), 2, 1),
                         substr(upper(trim(answer)), 4, 1),
                         substr(upper(trim(answer)), 5, 1)) then 1 else 0 end +
            case when substr(upper(trim(answer)), 4, 1)
                 not in (substr(upper(trim(answer)), 1, 1),
                         substr(upper(trim(answer)), 2, 1),
                         substr(upper(trim(answer)), 3, 1),
                         substr(upper(trim(answer)), 5, 1)) then 1 else 0 end +
            case when substr(upper(trim(answer)), 5, 1)
                 not in (substr(upper(trim(answer)), 1, 1),
                         substr(upper(trim(answer)), 2, 1),
                         substr(upper(trim(answer)), 3, 1),
                         substr(upper(trim(answer)), 4, 1)) then 1 else 0 end
        )                                               as unique_letter_count

    from source
    where answer is not null
      and length(trim(answer)) = 5

)

select * from cleaned