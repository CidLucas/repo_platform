# apps/hitl_dashboard/src/hitl_dashboard/app.py
"""
Streamlit HITL Dashboard - Human-in-the-Loop Review Interface.

Run with: streamlit run src/hitl_dashboard/app.py
"""

import os
from datetime import datetime
from uuid import UUID

import pandas as pd
import streamlit as st

from vizu_hitl_service import HitlQueue
from vizu_models import (
    HitlCriteriaType,
    HitlFeedbackType,
    HitlReviewRead,
    HitlReviewStatus,
)


class Settings:
    """Dashboard settings from environment."""
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    PAGE_SIZE: int = int(os.getenv("HITL_PAGE_SIZE", "20"))
    REFRESH_INTERVAL: int = int(os.getenv("HITL_REFRESH_INTERVAL", "30"))


def get_settings() -> Settings:
    return Settings()

# Page config
st.set_page_config(
    page_title="Vizu HITL Dashboard",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# CACHE & STATE
# ============================================================================

@st.cache_resource
def get_queue() -> HitlQueue:
    """Get or create HitlQueue instance."""
    settings = get_settings()
    return HitlQueue.from_url(settings.REDIS_URL)


def get_clients_with_pending() -> list[str]:
    """Get list of client IDs with pending reviews."""
    queue = get_queue()
    stats = queue.get_stats()
    return list(stats.by_client.keys())


# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar():
    """Render sidebar with filters and stats."""
    st.sidebar.title("👁️ HITL Dashboard")
    st.sidebar.markdown("---")

    # Stats
    queue = get_queue()
    stats = queue.get_stats()

    st.sidebar.metric("📋 Pendentes", stats.total_pending)
    st.sidebar.metric("📊 Total Hoje", stats.total_today)

    if stats.oldest_pending_hours:
        st.sidebar.metric("⏰ Mais Antiga", f"{stats.oldest_pending_hours:.1f}h")

    st.sidebar.markdown("---")

    # Filters
    st.sidebar.subheader("🔍 Filtros")

    # Client filter
    clients = get_clients_with_pending()
    selected_client = st.sidebar.selectbox(
        "Cliente",
        options=["Todos"] + clients,
        index=0,
    )

    # Criteria filter
    criteria_options = ["Todos"] + [c.value for c in HitlCriteriaType]
    selected_criteria = st.sidebar.selectbox(
        "Critério",
        options=criteria_options,
        index=0,
    )

    # Store in session state
    st.session_state["filter_client"] = None if selected_client == "Todos" else selected_client
    st.session_state["filter_criteria"] = None if selected_criteria == "Todos" else selected_criteria

    st.sidebar.markdown("---")

    # Refresh
    if st.sidebar.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # By criteria stats
    if stats.by_criteria:
        st.sidebar.subheader("📊 Por Critério")
        for criteria, count in stats.by_criteria.items():
            st.sidebar.text(f"{criteria}: {count}")


# ============================================================================
# MAIN CONTENT
# ============================================================================

def render_review_card(review: HitlReviewRead, index: int):
    """Render a single review card."""

    with st.container():
        # Header
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            st.markdown(f"**Session:** `{review.session_id[:20]}...`")
            if review.trace_id:
                st.markdown(f"🔗 [Langfuse Trace]({get_settings().LANGFUSE_HOST}/trace/{review.trace_id})")

        with col2:
            criteria_emoji = {
                "low_confidence": "📉",
                "elicitation_pending": "❓",
                "tool_call_failed": "⚠️",
                "keyword_trigger": "🔤",
                "first_n_messages": "🆕",
                "random_sample": "🎲",
                "manual_flag": "🚩",
                "sentiment_negative": "😠",
                "long_response_time": "🐢",
            }
            emoji = criteria_emoji.get(review.criteria_triggered, "📋")
            st.markdown(f"{emoji} **{review.criteria_triggered}**")

            if review.confidence_score is not None:
                score_color = "🟢" if review.confidence_score > 0.7 else "🟡" if review.confidence_score > 0.5 else "🔴"
                st.markdown(f"{score_color} Confiança: {review.confidence_score:.2f}")

        with col3:
            age = datetime.utcnow() - review.created_at
            if age.total_seconds() < 3600:
                age_str = f"{int(age.total_seconds() / 60)}min"
            else:
                age_str = f"{age.total_seconds() / 3600:.1f}h"
            st.markdown(f"⏱️ {age_str}")

        st.markdown("---")

        # Messages
        col_msg, col_resp = st.columns(2)

        with col_msg:
            st.markdown("**👤 Usuário:**")
            st.info(review.user_message)

        with col_resp:
            st.markdown("**🤖 Agente:**")
            st.success(review.agent_response)

        # Tools called
        if review.tools_called:
            st.markdown(f"**🔧 Tools:** {', '.join(review.tools_called)}")

        # Action buttons
        st.markdown("---")
        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            if st.button("✅ Aprovar", key=f"approve_{index}", use_container_width=True):
                handle_approve(review)

        with col_b:
            if st.button("✏️ Corrigir", key=f"correct_{index}", use_container_width=True):
                st.session_state[f"editing_{index}"] = True

        with col_c:
            if st.button("❌ Rejeitar", key=f"reject_{index}", use_container_width=True):
                handle_reject(review)

        with col_d:
            if st.button("⬆️ Escalar", key=f"escalate_{index}", use_container_width=True):
                handle_escalate(review)

        # Correction form
        if st.session_state.get(f"editing_{index}"):
            render_correction_form(review, index)

        st.markdown("---")
        st.markdown("")  # Spacing


def render_correction_form(review: HitlReviewRead, index: int):
    """Render correction form for a review."""

    with st.form(key=f"correction_form_{index}"):
        corrected = st.text_area(
            "Resposta Corrigida",
            value=review.agent_response,
            height=150,
        )

        feedback_type = st.selectbox(
            "Tipo de Problema",
            options=[f.value for f in HitlFeedbackType],
            index=0,
        )

        notes = st.text_area("Notas (opcional)", height=80)

        tags = st.text_input("Tags (separadas por vírgula)")

        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Salvar Correção", use_container_width=True):
                handle_correct(
                    review=review,
                    corrected_response=corrected,
                    feedback_type=feedback_type,
                    notes=notes,
                    tags=[t.strip() for t in tags.split(",") if t.strip()],
                )
                st.session_state[f"editing_{index}"] = False
                st.rerun()

        with col2:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                st.session_state[f"editing_{index}"] = False
                st.rerun()


# ============================================================================
# HANDLERS
# ============================================================================

def get_reviewer_id() -> str:
    """Get current reviewer ID (from session or default)."""
    return st.session_state.get("reviewer_id", "anonymous")


def handle_approve(review: HitlReviewRead):
    """Handle approve action."""
    queue = get_queue()
    queue.update_review(
        review_id=review.id,
        status=HitlReviewStatus.APPROVED,
        reviewer_id=get_reviewer_id(),
        feedback_type=HitlFeedbackType.CORRECT.value,
    )
    st.success("✅ Aprovado!")
    st.cache_data.clear()
    st.rerun()


def handle_reject(review: HitlReviewRead):
    """Handle reject action."""
    queue = get_queue()
    queue.update_review(
        review_id=review.id,
        status=HitlReviewStatus.REJECTED,
        reviewer_id=get_reviewer_id(),
    )
    st.warning("❌ Rejeitado!")
    st.cache_data.clear()
    st.rerun()


def handle_escalate(review: HitlReviewRead):
    """Handle escalate action."""
    queue = get_queue()
    queue.update_review(
        review_id=review.id,
        status=HitlReviewStatus.ESCALATED,
        reviewer_id=get_reviewer_id(),
    )
    st.info("⬆️ Escalado!")
    st.cache_data.clear()
    st.rerun()


def handle_correct(
    review: HitlReviewRead,
    corrected_response: str,
    feedback_type: str,
    notes: str,
    tags: list[str],
):
    """Handle correction action."""
    queue = get_queue()
    queue.update_review(
        review_id=review.id,
        status=HitlReviewStatus.CORRECTED,
        reviewer_id=get_reviewer_id(),
        corrected_response=corrected_response,
        feedback_type=feedback_type,
        feedback_notes=notes if notes else None,
        feedback_tags=tags,
    )
    st.success("✏️ Correção salva!")


# ============================================================================
# PAGES
# ============================================================================

def page_pending():
    """Pending reviews page."""
    st.title("📋 Revisões Pendentes")

    queue = get_queue()

    # Get filter from session
    client_filter = st.session_state.get("filter_client")
    client_uuid = UUID(client_filter) if client_filter else None

    # Fetch reviews
    reviews = queue.get_pending(
        client_id=client_uuid,
        limit=get_settings().PAGE_SIZE,
    )

    if not reviews:
        st.info("🎉 Nenhuma revisão pendente!")
        return

    st.markdown(f"**{len(reviews)} revisões pendentes**")
    st.markdown("---")

    for i, review in enumerate(reviews):
        render_review_card(review, i)


def page_stats():
    """Statistics page."""
    st.title("📊 Estatísticas")

    queue = get_queue()
    stats = queue.get_stats()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Pendentes", stats.total_pending)
    with col2:
        st.metric("Total Hoje", stats.total_today)
    with col3:
        if stats.avg_review_time_minutes:
            st.metric("Tempo Médio", f"{stats.avg_review_time_minutes:.1f}min")
        else:
            st.metric("Tempo Médio", "—")

    st.markdown("---")

    # By criteria chart
    if stats.by_criteria:
        st.subheader("Por Critério")
        df = pd.DataFrame([
            {"Critério": k, "Quantidade": v}
            for k, v in stats.by_criteria.items()
        ])
        st.bar_chart(df.set_index("Critério"))

    # By client chart
    if stats.by_client:
        st.subheader("Por Cliente")
        df = pd.DataFrame([
            {"Cliente": k[:8] + "...", "Quantidade": v}
            for k, v in stats.by_client.items()
        ])
        st.bar_chart(df.set_index("Cliente"))


def page_settings():
    """Settings page."""
    st.title("⚙️ Configurações")

    st.subheader("👤 Revisor")
    reviewer_id = st.text_input(
        "Seu ID/Email",
        value=st.session_state.get("reviewer_id", ""),
        placeholder="seu@email.com"
    )
    if reviewer_id:
        st.session_state["reviewer_id"] = reviewer_id
        st.success(f"Revisor definido: {reviewer_id}")

    st.markdown("---")

    st.subheader("🔧 Manutenção")

    if st.button("🗑️ Expirar revisões antigas (24h+)"):
        queue = get_queue()
        expired = queue.expire_old_reviews(max_age_hours=24)
        st.info(f"Expiradas: {expired} revisões")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main app entry point."""
    render_sidebar()

    # Navigation
    page = st.sidebar.radio(
        "Navegação",
        options=["📋 Pendentes", "📊 Estatísticas", "📤 Datasets", "⚙️ Configurações"],
        label_visibility="collapsed",
    )

    if page == "📋 Pendentes":
        page_pending()
    elif page == "📊 Estatísticas":
        page_stats()
    elif page == "📤 Datasets":
        from .pages.datasets import render_page as datasets_page
        datasets_page()
    elif page == "⚙️ Configurações":
        page_settings()


if __name__ == "__main__":
    main()
