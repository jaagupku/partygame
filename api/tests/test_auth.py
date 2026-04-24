from partygame.service.auth import hash_password, verify_password


def test_password_hash_does_not_store_plaintext():
    password_hash = hash_password("correct horse battery staple")

    assert "correct horse battery staple" not in password_hash
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)
