import requests

def test_ollama_health_check():
    """
    Testa se o servidor Ollama responde ao health check na porta 11434.
    """
    response = requests.get("http://localhost:11434")
    assert response.status_code == 200
