from pydantic import BaseModel, ConfigDict

class CoreModel(BaseModel):
    """
    Modelo base para todos os outros modelos do projeto.
    Define configurações Pydantic globais.
    """
    model_config = ConfigDict(from_attributes=True)

class BaseSchema(CoreModel):
    """
    Schema base para modelos que representam entidades do banco.
    """
    pass