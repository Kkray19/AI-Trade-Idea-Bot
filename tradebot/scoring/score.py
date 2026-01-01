import math

def idea_score(popularity: int, comments: int, age_hours: float):
    pop = math.log1p(max(popularity, 0)) + 0.6 * math.log1p(max(comments, 0))
    decay = math.exp(-0.15 * max(age_hours, 0))
    return pop * decay
