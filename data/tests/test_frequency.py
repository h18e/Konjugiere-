from pipeline.frequency import rank


def test_rank_sums_forms_and_splits_shared_forms():
    verbs = {"être": {"suis", "est"}, "suivre": {"suis", "suit"}, "parler": {"parle"}}
    counts = {"suis": 100, "est": 300, "suit": 10, "parle": 40}
    # être = 50 + 300, suivre = 50 + 10, parler = 40
    assert rank(verbs, counts) == {"être": 1, "suivre": 2, "parler": 3}


def test_verbs_without_hits_get_no_rank():
    assert rank({"x": {"zzz"}}, {"a": 1}) == {}
