from quantcrawl.policy import PolicyResolver


def test_policy_resolver_precedence() -> None:
    resolver = PolicyResolver(
        default_profile={
            "fingerprint_mode": "web_only",
            "challenge_enabled": False,
            "max_challenge_attempts": 1,
        },
        spider_profiles={
            "s1": {
                "fingerprint_mode": "hybrid",
                "challenge_enabled": True,
            }
        },
    )

    profile = resolver.resolve("s1")
    assert profile.fingerprint_mode == "hybrid"
    assert profile.challenge_enabled is True
    assert profile.max_challenge_attempts == 1


def test_policy_resolver_3d_precedence() -> None:
    resolver = PolicyResolver(
        default_profile={
            "challenge_enabled": False,
            "solver_provider_ref": "default",
            "max_challenge_attempts": 1,
        },
        spider_profiles={
            "s1": {
                "solver_provider_ref": "spider",
                "source_profiles": {
                    "czce": {
                        "challenge_enabled": True,
                        "max_challenge_attempts": 2,
                    },
                },
                "source_dataset_profiles": {
                    "czce:exchange_notice_demo": {
                        "solver_provider_ref": "s1_czce_notice",
                        "max_challenge_attempts": 3,
                    },
                },
            },
        },
    )

    profile = resolver.resolve(
        spider_name="s1",
        source="czce",
        dataset="exchange_notice_demo",
    )
    assert profile.challenge_enabled is True
    assert profile.solver_provider_ref == "s1_czce_notice"
    assert profile.max_challenge_attempts == 3

    source_only_profile = resolver.resolve(
        spider_name="s1",
        source="czce",
        dataset="unknown",
    )
    assert source_only_profile.challenge_enabled is True
    assert source_only_profile.solver_provider_ref == "spider"
    assert source_only_profile.max_challenge_attempts == 2


def test_policy_resolver_validates_allowed_challenge_types() -> None:
    try:
        PolicyResolver(
            default_profile={
                "allowed_challenge_types": ["bad_type"],
            },
            spider_profiles={},
        )
    except ValueError as exc:
        assert "allowed_challenge_types" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for invalid allowed_challenge_types")


def test_policy_resolver_validates_dimension_profile_shape() -> None:
    try:
        PolicyResolver(
            default_profile={},
            spider_profiles={
                "s1": {
                    "source_profiles": {
                        "czce": "invalid",
                    },
                },
            },
        )
    except ValueError as exc:
        assert "source_profiles" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for invalid source_profiles shape")
