from hackman_control_deck.statistics import StatisticsStore


def test_statistics_are_local_per_profile_and_can_be_reset(tmp_path) -> None:
    store = StatisticsStore(tmp_path / "statistics.json")
    store.record("Fusion", "1", "short")
    store.record("Fusion", "1", "long")
    store.record("Default", "1", "short")

    assert store.counts("Fusion")["1"] == {"short": 1, "long": 1}
    assert store.counts("Default")["1"] == {"short": 1, "long": 0}

    store.reset("Fusion")

    assert store.counts("Fusion") == {}
    assert store.counts("Default")["1"]["short"] == 1
