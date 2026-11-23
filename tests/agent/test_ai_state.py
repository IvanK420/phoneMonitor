import pytest

from agent.ai_sessions import classify, session_state


# --- 3.1 Heuristique sur l'âge (02-api.md) ----------------------------------


@pytest.mark.parametrize(
    ("age_s", "state"),
    [(0, "working"), (9, "working"), (10, "idle"), (599, "idle"), (600, "stale"), (86_400, "stale")],
)
def test_classify_by_age(age_s, state):
    assert classify(age_s) == state


def test_classify_future_timestamp_counts_as_working():
    # Horloges légèrement décalées : un fichier « dans le futur » vient d'être écrit.
    assert classify(-3) == "working"


# --- 3.3 Le statut explicite prime sur l'heuristique ----------------------------


def test_busy_status_is_working_even_if_heuristic_says_idle():
    assert session_state("busy", age_s=120) == "working"


def test_idle_status_is_idle_even_if_just_updated():
    assert session_state("idle", age_s=1) == "idle"


def test_stale_wins_over_explicit_status():
    # Session plantée : le fichier dit encore « busy » mais n'a plus bougé depuis 10 min.
    assert session_state("busy", age_s=600) == "stale"


@pytest.mark.parametrize("status", [None, "", "waiting", 42])
def test_unknown_status_falls_back_to_heuristic(status):
    assert session_state(status, age_s=5) == "working"
    assert session_state(status, age_s=60) == "idle"
