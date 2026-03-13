"""Tests for the Sphinx extension."""


def test_setup_returns_version() -> None:
    """setup() returns a dict with version and parallel flags."""
    from sphinx_literalizer import setup

    result = setup(app=None)  # type: ignore[arg-type]
    assert result["version"] == "0.1.0"
    assert result["parallel_read_safe"] is True
    assert result["parallel_write_safe"] is True


def test_extension_can_be_imported() -> None:
    """Extension module can be imported."""
    import sphinx_literalizer

    assert hasattr(sphinx_literalizer, "setup")
