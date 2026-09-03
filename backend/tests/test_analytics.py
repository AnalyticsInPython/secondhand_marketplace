"""The research questions run end to end on the seeded corpus."""

import pandas as pd

from app.analytics import questions
from app.analytics.frames import load as load_frames
from scripts.seed import load as load_corpus


def test_every_question_returns_a_frame():
    counts = load_corpus(do_reset=True, limit=120, demo_email="demo@columbia.edu")
    assert counts["listings"] == 120
    assert counts["external_skipped"] > 0  # the corpus still carries the tier; the loader drops it
    frames = load_frames()
    assert len(frames["listings"]) == 123  # 120 from the corpus + 3 demo listings
    assert "source" not in frames["listings"].columns
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
