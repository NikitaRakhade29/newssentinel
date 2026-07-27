from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    if not text:
        return {'compound': 0.0, 'sentiment_label': 'Neutral'}
    
    scores = analyzer.polarity_scores(text)
    compound = scores['compound']
    
    if compound >= 0.05:
        label = 'Positive'
    elif compound <= -0.05:
        label = 'Negative'
    else:
        label = 'Neutral'
        
    return {
        'compound': compound,
        'sentiment_label': label
    }

if __name__ == "__main__":
    sample = "NVIDIA announces groundbreaking AI hardware with 5x efficiency"
    res = analyze_sentiment(sample)
    print(f"Sample: {sample}")
    print(f"Result: {res}")
