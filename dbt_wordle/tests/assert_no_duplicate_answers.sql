-- assert_no_duplicate_answers.sql
-- Custom test: fails if any word appears more than once as a Wordle answer.
-- dbt tests pass when this query returns 0 rows.

select
    puzzle_number,
    answer,
    count(*) as times_used
from {{ ref('stg_wordle_words') }}
group by puzzle_number, answer
having count(*) > 1