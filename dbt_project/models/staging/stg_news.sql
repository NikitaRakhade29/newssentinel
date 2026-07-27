with raw_data as (
    select * from read_parquet('../data/bronze_news/*.parquet')
)

select
    cast(story_id as varchar) as story_id,
    trim(title) as title,
    url,
    author,
    cast(score as integer) as upvotes,
    cast(comments as integer) as comment_count,
    cast(sentiment_score as double) as sentiment_score,
    sentiment_label,
    to_timestamp(cast(created_at as bigint)) as published_at,
    cast(ingested_at as timestamp) as ingested_at
from raw_data
