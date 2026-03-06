-- mart_letter_frequency
-- Materialization: table
-- Overall letter frequency across all Wordle answers.
-- Direct source for dashboard bar chart.

select
    letter,
    total_count,
    frequency_pct,
    frequency_rank
from {{ ref('int_letter_frequency') }}
order by total_count desc