import random

from faker import Faker


def make_rng(seed: int) -> random.Random:
    return random.Random(seed)


def make_faker(rng: random.Random) -> Faker:
    fake = Faker("en_US")
    fake.seed_instance(rng.randint(0, 2**32 - 1))
    return fake
