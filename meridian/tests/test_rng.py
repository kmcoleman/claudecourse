from meridian.rng import make_rng, make_faker


def test_make_rng_is_deterministic():
    a = make_rng(42)
    b = make_rng(42)
    assert [a.random() for _ in range(5)] == [b.random() for _ in range(5)]


def test_make_faker_is_deterministic():
    fa = make_faker(make_rng(42))
    fb = make_faker(make_rng(42))
    assert [fa.name() for _ in range(5)] == [fb.name() for _ in range(5)]


def test_different_seeds_differ():
    assert make_rng(1).random() != make_rng(2).random()
