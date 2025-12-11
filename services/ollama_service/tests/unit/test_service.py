from unittest.mock import MagicMock


def test_dummy_ollama():
    mock = MagicMock()
    mock.run_model.return_value = True
    assert mock.run_model() is True
