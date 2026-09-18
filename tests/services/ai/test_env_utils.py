from writer.services.ai.env_utils import resolve_env_var


def test_resolve_env_var_from_dict():
    fake_env = {"TEST_KEY": "  secret_123  "}
    assert resolve_env_var("TEST_KEY", environ=fake_env) == "secret_123"
    assert resolve_env_var("NON_EXISTENT", environ=fake_env) == ""
