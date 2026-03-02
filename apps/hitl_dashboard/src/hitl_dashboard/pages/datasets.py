# apps/hitl_dashboard/src/hitl_dashboard/pages/datasets.py
"""
Langfuse Dataset Management Page.

Permite visualizar e gerenciar datasets criados a partir de revisões HITL.
"""

import os

import streamlit as st

from vizu_hitl_service import HitlQueue, LangfuseDatasetManager


class Settings:
    """Dashboard settings from environment."""
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
    PAGE_SIZE: int = int(os.getenv("HITL_PAGE_SIZE", "20"))
    REFRESH_INTERVAL: int = int(os.getenv("HITL_REFRESH_INTERVAL", "30"))


def get_settings() -> Settings:
    return Settings()


def render_page():
    """Render datasets page."""
    st.title("📊 Langfuse Datasets")

    # Check if Langfuse is configured
    settings = get_settings()
    if not settings.LANGFUSE_SECRET_KEY:
        st.warning(
            "⚠️ Langfuse não configurado. "
            "Defina LANGFUSE_SECRET_KEY e LANGFUSE_PUBLIC_KEY."
        )
        return

    manager = LangfuseDatasetManager()
    if not manager.enabled:
        st.error("❌ Falha ao conectar ao Langfuse")
        return

    st.markdown("---")

    # Tab layout
    tab1, tab2 = st.tabs(["📤 Exportar Reviews", "📋 Datasets Existentes"])

    with tab1:
        render_export_section(manager)

    with tab2:
        render_existing_datasets(manager)


def render_export_section(manager: LangfuseDatasetManager):
    """Section to export approved reviews to a dataset."""
    st.subheader("Exportar Reviews Aprovadas")

    _queue = HitlQueue.from_url(get_settings().REDIS_URL)  # noqa: F841

    # Get reviewed items (not just pending)
    # Note: This would need a method to get completed reviews

    col1, col2 = st.columns(2)

    with col1:
        dataset_name = st.text_input(
            "Nome do Dataset",
            value="hitl-golden-set",
            help="Nome do dataset no Langfuse"
        )

    with col2:
        _include_corrected = st.checkbox(  # noqa: F841
            "Incluir correções",
            value=True,
            help="Usar respostas corrigidas quando disponíveis"
        )

    st.markdown("---")

    # Manual export form
    st.markdown("### Exportar manualmente")

    with st.form("manual_export"):
        user_message = st.text_area("Mensagem do usuário", height=100)
        expected_response = st.text_area("Resposta esperada", height=100)

        tags = st.text_input("Tags (separadas por vírgula)")

        if st.form_submit_button("➕ Adicionar ao Dataset"):
            if user_message and expected_response:
                dataset = manager.get_or_create_dataset(dataset_name)
                if dataset:
                    try:
                        item = dataset.create_item(
                            input={"message": user_message},
                            expected_output=expected_response,
                            metadata={
                                "source": "manual",
                                "tags": [t.strip() for t in tags.split(",") if t.strip()]
                            }
                        )
                        st.success(f"✅ Item adicionado ao dataset: {item.id}")
                    except Exception as e:
                        st.error(f"❌ Erro: {e}")
                else:
                    st.error("❌ Falha ao acessar dataset")
            else:
                st.warning("Preencha a mensagem e a resposta esperada")


def render_existing_datasets(manager: LangfuseDatasetManager):
    """Show existing datasets."""
    st.subheader("Datasets no Langfuse")

    client = manager._get_client()
    if not client:
        st.error("Não foi possível conectar ao Langfuse")
        return

    try:
        # Note: Langfuse SDK might not have list_datasets
        # This is a placeholder for the actual implementation
        st.info(
            "💡 Acesse o Langfuse diretamente para visualizar seus datasets:\n\n"
            f"🔗 [{get_settings().LANGFUSE_HOST}]({get_settings().LANGFUSE_HOST})"
        )

        st.markdown("---")

        # Quick links
        st.markdown("### Links Rápidos")
        st.markdown(f"- [Datasets]({get_settings().LANGFUSE_HOST}/project/datasets)")
        st.markdown(f"- [Experimentos]({get_settings().LANGFUSE_HOST}/project/experiments)")
        st.markdown(f"- [Traces]({get_settings().LANGFUSE_HOST}/project/traces)")

    except Exception as e:
        st.error(f"Erro ao listar datasets: {e}")


if __name__ == "__main__":
    render_page()
