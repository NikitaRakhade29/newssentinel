with staging as (
    select * from {{ ref('stg_news') }}
)

select
    sentiment_label,
    count(distinct story_id) as total_stories,
    round(avg(sentiment_score), 4) as avg_sentiment_score,
    sum(upvotes) as total_upvotes,
    sum(comment_count) as total_comments,
    max(published_at) as latest_story_time
from staging
group by sentiment_label
