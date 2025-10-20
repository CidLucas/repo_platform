from unittest.mock import MagicMock

def test_dummy_knowledge_base():
    mock = MagicMock()
    mock.query.return_value = True
    assert mock.query() is True
