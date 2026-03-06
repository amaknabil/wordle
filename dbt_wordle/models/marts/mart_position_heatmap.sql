-- mart_position_heatmap
-- Materialization: table
-- Letter frequency per position (1–5) for dashboard heatmap.
-- Each row = one letter in one position with its count and percentage.

select
    position,
    letter,
    position_count,
    position_pct
from {{ ref('int_position_frequency') }}
order by position, position_count desc