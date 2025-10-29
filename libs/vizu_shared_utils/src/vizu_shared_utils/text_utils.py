# libs/vizu_shared_utils/text_utils.py
import unicodedata
import re

def normalize_text(text: str) -> str:
    """
    Aplica a normalização padrão Vizu:
    1. Remove acentos (decomposição NFD).
    2. Converte para minúsculas.
    3. Remove espaços extras.
    """
    if not isinstance(text, str):
        return str(text) # Garante que é string

    # 1. Remove acentos (Ex: "Produto" -> "Produto")
    nfkd_form = unicodedata.normalize('NFD', text)
    text = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    
    # 2. Converte para minúsculas
    text = text.lower()
    
    # 3. Remove espaços extras no início/fim
    text = text.strip()
    
    # 4. (Opcional) Remove caracteres especiais, exceto espaço
    # text = re.sub(r'[^a-z0-9\s]', '', text) 
    
    return text