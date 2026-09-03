"""The research questions run end to end on seeded data."""

import pandas as pd

from app.analytics import questions
from app.analytics.frames import load
from scripts.seed import seed


def test_every_question_returns_a_frame():
    seed(40, 80, do_reset=True, demo_email="demo@columbia.edu")
    frames = load()
    assert len(frames["listings"]) == 83
    for fn in (
        questions.badge_experiment,
        questions.inventory_by_filter_depth,
        questions.filter_usage,
        questions.price_guidance,
        questions.seasonality,
        questions.funnel,
        questions.days_to_sell,
    ):
        out = fn(frames)
        assert isinstance(out, pd.DataFrame), fn.__name__
        assert "note" not in out.columns, f"{fn.__name__} found no data"
