from meridian.identity import make_identity, email_for
from meridian.rng import make_rng, make_faker


def test_email_is_deterministic_from_name():
    assert email_for("Bob Smith") == "bob.smith@meridian-energy.com"


def test_no_mismatch_account_matches_name():
    rng = make_rng(1)
    fake = make_faker(rng)
    full, account, email = make_identity(fake, rng, mismatch=False)
    # account_name is a normalized form of the full name
    assert account.replace(".", " ").split()[0].lower() in full.lower()


def test_mismatch_breaks_name_join():
    rng = make_rng(1)
    fake = make_faker(rng)
    full, account, email = make_identity(fake, rng, mismatch=True)
    # the account_name is NOT the plain firstname.lastname form
    assert account != full.lower().replace(" ", ".")
    # but the email still resolves to the person
    assert email == email_for(full)
