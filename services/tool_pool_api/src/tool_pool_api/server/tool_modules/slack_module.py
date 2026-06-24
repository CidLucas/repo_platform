# tool_pool_api/server/tool_modules/slack_module.py
"""
Módulo Slack - Ferramentas de Comunicação

Integração com a API do Slack para listagem de canais,
leitura de mensagens, resumo de canais e envio de mensagens.
"""

import logging
from datetime import datetime, timedelta

import httpx
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from tool_pool_api.server.dependencies import get_context_service
from tool_pool_api.server.tool_modules import register_module

# Bind mcp_inject_client_id to its already-configured form so it can be used
# as a plain @decorator below. The factory signature is
#     mcp_inject_client_id(get_context_service_fn) -> decorator
# and the tools in this module use the @mcp_inject_client_id sugar form
# (which would otherwise pass the tool function as get_context_service_fn,
# breaking FastMCP's Pydantic schema generation). This rebind keeps the
# @mcp_inject_client_id syntax working without touching every tool.
mcp_inject_client_id = mcp_inject_client_id(get_context_service)

logger = logging.getLogger(__name__)

SLACK_API_URL = "https://slack.com/api"


# =============================================================================
# HELPERS
# =============================================================================


async def _get_slack_token(client_id: str) -> str:
    """Fetch Slack token from integration_tokens or credencial_servico_externo."""
    ctx = get_context_service()
    try:
        tokens = await ctx.get_integration_tokens(client_id, "slack", auto_refresh=False)
        if tokens and tokens.get("access_token"):
            return tokens["access_token"]
    except Exception:
        pass
    # fallback to credencial_servico_externo
    from blu_supabase_client import get_supabase_client

    supabase = get_supabase_client()
    r = (
        supabase.table("credencial_servico_externo")
        .select("valor")
        .eq("client_id", client_id)
        .eq("servico", "slack")
        .limit(1)
        .execute()
    )
    if r.data:
        return r.data[0]["valor"]
    raise ToolError(
        "Slack não conectado. Vá em Admin > Integrações para conectar."
    )


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


async def _slack_list_channels_logic(
    client_id: str,
    limit: int = 50,
) -> dict:
    """
    Lista os canais do Slack do cliente.

    Args:
        limit: Máximo de canais a retornar (padrão 50)

    Returns:
        Dict com {total, channels: [{id, name, purpose, num_members, is_private}]}
    """
    try:
        token = await _get_slack_token(client_id)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{SLACK_API_URL}/conversations.list",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": limit, "exclude_archived": "true"},
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise ToolError(f"Slack API error: {data.get('error', 'unknown')}")

        channels = [
            {
                "id": ch["id"],
                "name": ch.get("name", ""),
                "purpose": ch.get("purpose", {}).get("value", ""),
                "num_members": ch.get("num_members", 0),
                "is_private": ch.get("is_private", False),
            }
            for ch in data.get("channels", [])
        ]
        logger.info(f"[Slack] Listed {len(channels)} channels for client_id={client_id}")
        return {"total": len(channels), "channels": channels}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Slack] Error listing channels: {e}")
        raise ToolError(f"Erro ao listar canais do Slack: {e}")


async def _slack_read_channel_logic(
    client_id: str,
    channel_id: str,
    limit: int = 30,
    oldest_hours: int = 24,
) -> dict:
    """
    Lê mensagens recentes de um canal do Slack.

    Args:
        channel_id: ID do canal
        limit: Máximo de mensagens (padrão 30)
        oldest_hours: Quantas horas atrás buscar (padrão 24)

    Returns:
        Dict com {channel_id, messages: [{user_name, text, ts, formatted_time}]}
    """
    try:
        token = await _get_slack_token(client_id)
        oldest = str((datetime.now() - timedelta(hours=oldest_hours)).timestamp())

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{SLACK_API_URL}/conversations.history",
                headers={"Authorization": f"Bearer {token}"},
                params={"channel": channel_id, "limit": limit, "oldest": oldest},
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                raise ToolError(f"Slack API error: {data.get('error', 'unknown')}")

            raw_messages = data.get("messages", [])

            # Fetch user names with caching
            user_cache: dict[str, str] = {}
            messages = []
            for msg in raw_messages:
                uid = msg.get("user")
                if uid and uid not in user_cache:
                    try:
                        u_resp = await client.get(
                            f"{SLACK_API_URL}/users.info",
                            headers={"Authorization": f"Bearer {token}"},
                            params={"user": uid},
                        )
                        u_data = u_resp.json()
                        if u_data.get("ok"):
                            user_cache[uid] = (
                                u_data["user"].get("profile", {}).get("display_name")
                                or u_data["user"].get("real_name", uid)
                            )
                        else:
                            user_cache[uid] = uid
                    except Exception:
                        user_cache[uid] = uid

                user_name = user_cache.get(uid, uid) if uid else "bot"
                ts = msg.get("ts", "0")
                try:
                    formatted_time = datetime.fromtimestamp(float(ts)).strftime("%H:%M")
                except Exception:
                    formatted_time = ts

                messages.append(
                    {
                        "user_name": user_name,
                        "text": msg.get("text", ""),
                        "ts": ts,
                        "formatted_time": formatted_time,
                    }
                )

        logger.info(
            f"[Slack] Read {len(messages)} messages from channel {channel_id} for client_id={client_id}"
        )
        return {"channel_id": channel_id, "messages": messages}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Slack] Error reading channel: {e}")
        raise ToolError(f"Erro ao ler canal {channel_id}: {e}")


async def _slack_summarize_channel_logic(
    client_id: str,
    channel_id: str,
    hours: int = 48,
) -> dict:
    """
    Resume as últimas mensagens de um canal do Slack.

    Args:
        channel_id: ID do canal
        hours: Quantas horas atrás buscar (padrão 48)

    Returns:
        Dict com {channel_id, hours, message_count, participants, summary_text}
    """
    try:
        token = await _get_slack_token(client_id)
        oldest = str((datetime.now() - timedelta(hours=hours)).timestamp())

        async with httpx.AsyncClient(timeout=30) as client:
            # Get channel name
            ci_resp = await client.get(
                f"{SLACK_API_URL}/conversations.info",
                headers={"Authorization": f"Bearer {token}"},
                params={"channel": channel_id},
            )
            ci_data = ci_resp.json()
            channel_name = (
                ci_data.get("channel", {}).get("name", channel_id)
                if ci_data.get("ok")
                else channel_id
            )

            # Get messages
            hist_resp = await client.get(
                f"{SLACK_API_URL}/conversations.history",
                headers={"Authorization": f"Bearer {token}"},
                params={"channel": channel_id, "limit": 100, "oldest": oldest},
            )
            hist_data = hist_resp.json()

            if not hist_data.get("ok"):
                raise ToolError(f"Slack API error: {hist_data.get('error', 'unknown')}")

            raw_messages = hist_data.get("messages", [])

            # Fetch user names with caching
            user_cache: dict[str, str] = {}
            messages = []
            for msg in raw_messages:
                uid = msg.get("user")
                if uid and uid not in user_cache:
                    try:
                        u_resp = await client.get(
                            f"{SLACK_API_URL}/users.info",
                            headers={"Authorization": f"Bearer {token}"},
                            params={"user": uid},
                        )
                        u_data = u_resp.json()
                        if u_data.get("ok"):
                            user_cache[uid] = (
                                u_data["user"].get("profile", {}).get("display_name")
                                or u_data["user"].get("real_name", uid)
                            )
                        else:
                            user_cache[uid] = uid
                    except Exception:
                        user_cache[uid] = uid

                user_name = user_cache.get(uid, uid) if uid else "bot"
                ts = msg.get("ts", "0")
                try:
                    formatted_time = datetime.fromtimestamp(float(ts)).strftime("%H:%M")
                except Exception:
                    formatted_time = ts

                messages.append(
                    {
                        "user_name": user_name,
                        "text": msg.get("text", ""),
                        "formatted_time": formatted_time,
                    }
                )

        names = list({m["user_name"] for m in messages if m["user_name"] != "bot"})
        N = len(messages)
        M = len(names)

        msg_lines = "\n".join(
            f"[{m['user_name']} {m['formatted_time']}]: {m['text'][:150]}"
            for m in messages
        )
        summary_text = (
            f"📢 #{channel_name} — últimas {hours}h\n"
            f"{N} msgs de {M} participantes\n"
            f"Participantes: {', '.join(names)}\n\n"
            f"Mensagens:\n{msg_lines}"
        )

        logger.info(
            f"[Slack] Summarized channel {channel_id}: {N} msgs, {M} participants"
        )
        return {
            "channel_id": channel_id,
            "hours": hours,
            "message_count": N,
            "participants": names,
            "summary_text": summary_text,
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Slack] Error summarizing channel: {e}")
        raise ToolError(f"Erro ao resumir canal {channel_id}: {e}")


async def _slack_list_dms_logic(
    client_id: str,
    limit: int = 20,
) -> dict:
    """
    Lista DMs e MPIMs do Slack.

    Args:
        limit: Máximo de conversas a retornar (padrão 20)

    Returns:
        Dict com {total, dms: [{id, type, display_name, is_group}]}
    """
    try:
        token = await _get_slack_token(client_id)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{SLACK_API_URL}/conversations.list",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "types": "im,mpim",
                    "limit": limit,
                    "exclude_archived": "true",
                },
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                raise ToolError(f"Slack API error: {data.get('error', 'unknown')}")

            user_cache: dict[str, str] = {}
            dms = []
            for ch in data.get("channels", []):
                is_mpim = ch.get("is_mpim", False)
                if is_mpim:
                    display_name = ch.get("name", ch["id"])
                else:
                    uid = ch.get("user", "")
                    if uid and uid not in user_cache:
                        try:
                            u_resp = await client.get(
                                f"{SLACK_API_URL}/users.info",
                                headers={"Authorization": f"Bearer {token}"},
                                params={"user": uid},
                            )
                            u_data = u_resp.json()
                            if u_data.get("ok"):
                                user_cache[uid] = (
                                    u_data["user"].get("profile", {}).get("display_name")
                                    or u_data["user"].get("real_name", uid)
                                )
                            else:
                                user_cache[uid] = uid
                        except Exception:
                            user_cache[uid] = uid
                    display_name = user_cache.get(uid, uid)

                dms.append(
                    {
                        "id": ch["id"],
                        "type": "mpim" if is_mpim else "im",
                        "display_name": display_name,
                        "is_group": is_mpim,
                    }
                )

        logger.info(f"[Slack] Listed {len(dms)} DMs for client_id={client_id}")
        return {"total": len(dms), "dms": dms}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Slack] Error listing DMs: {e}")
        raise ToolError(f"Erro ao listar DMs do Slack: {e}")


async def _slack_get_unread_logic(
    client_id: str,
    limit_per_channel: int = 5,
    max_channels: int = 10,
) -> dict:
    """
    Busca mensagens recentes (última 1h) de múltiplos canais.

    Args:
        limit_per_channel: Máximo de mensagens por canal (padrão 5)
        max_channels: Máximo de canais a verificar (padrão 10)

    Returns:
        Dict com {channels: [{channel_id, channel_name, messages}], total_messages}
    """
    try:
        token = await _get_slack_token(client_id)
        oldest = str((datetime.now() - timedelta(hours=1)).timestamp())

        async with httpx.AsyncClient(timeout=30) as client:
            list_resp = await client.get(
                f"{SLACK_API_URL}/conversations.list",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "types": "public_channel,private_channel,im",
                    "limit": max_channels,
                    "exclude_archived": "true",
                },
            )
            list_resp.raise_for_status()
            list_data = list_resp.json()

            if not list_data.get("ok"):
                raise ToolError(f"Slack API error: {list_data.get('error', 'unknown')}")

            raw_channels = list_data.get("channels", [])
            # Sort: IMs first, then channels
            raw_channels.sort(key=lambda c: (0 if c.get("is_im") else 1))

            user_cache: dict[str, str] = {}
            result_channels = []
            total_messages = 0

            for ch in raw_channels:
                ch_id = ch["id"]
                ch_name = ch.get("name", ch_id) if not ch.get("is_im") else ch_id

                hist_resp = await client.get(
                    f"{SLACK_API_URL}/conversations.history",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"channel": ch_id, "limit": limit_per_channel, "oldest": oldest},
                )
                hist_data = hist_resp.json()
                if not hist_data.get("ok"):
                    continue

                raw_msgs = hist_data.get("messages", [])
                if not raw_msgs:
                    continue

                messages = []
                for msg in raw_msgs:
                    uid = msg.get("user")
                    if uid and uid not in user_cache:
                        try:
                            u_resp = await client.get(
                                f"{SLACK_API_URL}/users.info",
                                headers={"Authorization": f"Bearer {token}"},
                                params={"user": uid},
                            )
                            u_data = u_resp.json()
                            if u_data.get("ok"):
                                user_cache[uid] = (
                                    u_data["user"].get("profile", {}).get("display_name")
                                    or u_data["user"].get("real_name", uid)
                                )
                            else:
                                user_cache[uid] = uid
                        except Exception:
                            user_cache[uid] = uid
                    user_name = user_cache.get(uid, uid) if uid else "bot"
                    messages.append(
                        {"user_name": user_name, "text": msg.get("text", ""), "ts": msg.get("ts", "0")}
                    )

                result_channels.append(
                    {"channel_id": ch_id, "channel_name": ch_name, "messages": messages}
                )
                total_messages += len(messages)

        logger.info(f"[Slack] Got unread for {len(result_channels)} channels, {total_messages} msgs")
        return {"channels": result_channels, "total_messages": total_messages}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Slack] Error getting unread: {e}")
        raise ToolError(f"Erro ao buscar mensagens não lidas do Slack: {e}")


async def _slack_search_messages_logic(
    client_id: str,
    query: str,
    count: int = 20,
    sort: str = "timestamp",
    sort_dir: str = "desc",
) -> dict:
    """
    Pesquisa mensagens no Slack.

    Args:
        query: Termo de busca
        count: Número de resultados (padrão 20)
        sort: Campo de ordenação (padrão 'timestamp')
        sort_dir: Direção da ordenação (padrão 'desc')

    Returns:
        Dict com {total, matches: [{text, channel_name, user, ts, permalink}]}
    """
    try:
        token = await _get_slack_token(client_id)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{SLACK_API_URL}/search.messages",
                headers={"Authorization": f"Bearer {token}"},
                params={"query": query, "count": count, "sort": sort, "sort_dir": sort_dir},
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise ToolError(f"Slack API error: {data.get('error', 'unknown')}")

        msgs_data = data.get("messages", {})
        matches = [
            {
                "text": m.get("text", ""),
                "channel_name": m.get("channel", {}).get("name", ""),
                "user": m.get("username") or m.get("user", ""),
                "ts": m.get("ts", ""),
                "permalink": m.get("permalink", ""),
            }
            for m in msgs_data.get("matches", [])
        ]

        logger.info(f"[Slack] Search '{query}' returned {len(matches)} results for client_id={client_id}")
        return {"total": msgs_data.get("total", len(matches)), "matches": matches}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Slack] Error searching messages: {e}")
        raise ToolError(f"Erro ao pesquisar mensagens no Slack: {e}")


async def _slack_add_reaction_logic(
    client_id: str,
    channel_id: str,
    timestamp: str,
    emoji_name: str,
) -> dict:
    """
    Adiciona uma reação (emoji) a uma mensagem do Slack.

    Args:
        channel_id: ID do canal
        timestamp: Timestamp da mensagem
        emoji_name: Nome do emoji sem dois-pontos (ex: thumbsup)

    Returns:
        Dict com {ok, error}
    """
    try:
        token = await _get_slack_token(client_id)
        # Strip colons if user passes :emoji:
        emoji_name = emoji_name.strip(":")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{SLACK_API_URL}/reactions.add",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"channel": channel_id, "timestamp": timestamp, "name": emoji_name},
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            error = data.get("error", "unknown")
            logger.warning(f"[Slack] Add reaction failed: {error}")
            return {"ok": False, "error": error}

        logger.info(f"[Slack] Added reaction :{emoji_name}: to {channel_id}/{timestamp}")
        return {"ok": True}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Slack] Error adding reaction: {e}")
        raise ToolError(f"Erro ao adicionar reação no Slack: {e}")


async def _slack_get_thread_replies_logic(
    client_id: str,
    channel_id: str,
    thread_ts: str,
    limit: int = 50,
) -> dict:
    """
    Busca respostas de um thread do Slack.

    Args:
        channel_id: ID do canal
        thread_ts: Timestamp do thread pai
        limit: Máximo de mensagens (padrão 50)

    Returns:
        Dict com {parent, replies, reply_count}
    """
    try:
        token = await _get_slack_token(client_id)

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{SLACK_API_URL}/conversations.replies",
                headers={"Authorization": f"Bearer {token}"},
                params={"channel": channel_id, "ts": thread_ts, "limit": limit},
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                raise ToolError(f"Slack API error: {data.get('error', 'unknown')}")

            all_messages = data.get("messages", [])
            user_cache: dict[str, str] = {}

            async def resolve_user(uid: str) -> str:
                if not uid:
                    return "bot"
                if uid in user_cache:
                    return user_cache[uid]
                try:
                    u_resp = await client.get(
                        f"{SLACK_API_URL}/users.info",
                        headers={"Authorization": f"Bearer {token}"},
                        params={"user": uid},
                    )
                    u_data = u_resp.json()
                    if u_data.get("ok"):
                        name = (
                            u_data["user"].get("profile", {}).get("display_name")
                            or u_data["user"].get("real_name", uid)
                        )
                        user_cache[uid] = name
                        return name
                except Exception:
                    pass
                user_cache[uid] = uid
                return uid

            def fmt_msg(msg: dict) -> dict:
                return {
                    "user_name": user_cache.get(msg.get("user", ""), msg.get("user", "bot")),
                    "text": msg.get("text", ""),
                    "ts": msg.get("ts", ""),
                }

            # Resolve all users first
            for msg in all_messages:
                await resolve_user(msg.get("user", ""))

            parent = fmt_msg(all_messages[0]) if all_messages else {}
            replies = [fmt_msg(m) for m in all_messages[1:]]

        logger.info(f"[Slack] Got {len(replies)} replies for thread {thread_ts} in {channel_id}")
        return {"parent": parent, "replies": replies, "reply_count": len(replies)}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Slack] Error getting thread replies: {e}")
        raise ToolError(f"Erro ao buscar respostas do thread {thread_ts}: {e}")


async def _slack_post_message_logic(
    client_id: str,
    channel_id: str,
    text: str,
    thread_ts: str | None = None,
) -> dict:
    """
    Envia uma mensagem para um canal do Slack.

    Args:
        channel_id: ID do canal
        text: Texto da mensagem
        thread_ts: Timestamp do thread para responder (opcional)

    Returns:
        Dict com {ok, ts, channel}
    """
    try:
        token = await _get_slack_token(client_id)
        body: dict = {"channel": channel_id, "text": text}
        if thread_ts:
            body["thread_ts"] = thread_ts

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{SLACK_API_URL}/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise ToolError(f"Slack API error: {data.get('error', 'unknown')}")

        logger.info(
            f"[Slack] Posted message to channel {channel_id} for client_id={client_id}"
        )
        return {"ok": data.get("ok"), "ts": data.get("ts"), "channel": data.get("channel")}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Slack] Error posting message: {e}")
        raise ToolError(f"Erro ao enviar mensagem para {channel_id}: {e}")


# =============================================================================
# REGISTRO DE TOOLS
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register Slack tools with the MCP server."""

    @mcp.tool
    @mcp_inject_client_id
    async def slack_list_channels(
        ctx: Context,
        client_id: str | None = None,
        limit: int = 50,
    ) -> dict:
        """
        Lista os canais do Slack disponíveis para o cliente.

        Args:
            limit: Máximo de canais a retornar (padrão 50)

        Returns:
            Dict com {total, channels: [{id, name, purpose, num_members, is_private}]}
        """
        return await _slack_list_channels_logic(client_id=client_id, limit=limit)

    @mcp.tool
    @mcp_inject_client_id
    async def slack_read_channel(
        ctx: Context,
        channel_id: str,
        client_id: str | None = None,
        limit: int = 30,
        oldest_hours: int = 24,
    ) -> dict:
        """
        Lê mensagens recentes de um canal do Slack.

        Args:
            channel_id: ID do canal (ex: C01234567)
            limit: Máximo de mensagens a retornar (padrão 30)
            oldest_hours: Quantas horas atrás buscar (padrão 24)

        Returns:
            Dict com {channel_id, messages: [{user_name, text, ts, formatted_time}]}
        """
        return await _slack_read_channel_logic(
            client_id=client_id,
            channel_id=channel_id,
            limit=limit,
            oldest_hours=oldest_hours,
        )

    @mcp.tool
    @mcp_inject_client_id
    async def slack_summarize_channel(
        ctx: Context,
        channel_id: str,
        client_id: str | None = None,
        hours: int = 48,
    ) -> dict:
        """
        Resume as últimas mensagens de um canal do Slack.

        Args:
            channel_id: ID do canal (ex: C01234567)
            hours: Quantas horas atrás incluir no resumo (padrão 48)

        Returns:
            Dict com {channel_id, hours, message_count, participants, summary_text}
        """
        return await _slack_summarize_channel_logic(
            client_id=client_id,
            channel_id=channel_id,
            hours=hours,
        )

    @mcp.tool
    @mcp_inject_client_id
    async def slack_post_message(
        ctx: Context,
        channel_id: str,
        text: str,
        client_id: str | None = None,
        thread_ts: str | None = None,
    ) -> dict:
        """
        Envia uma mensagem para um canal do Slack.

        Args:
            channel_id: ID do canal (ex: C01234567)
            text: Texto da mensagem
            thread_ts: Timestamp do thread para responder (opcional)

        Returns:
            Dict com {ok, ts, channel}
        """
        return await _slack_post_message_logic(
            client_id=client_id,
            channel_id=channel_id,
            text=text,
            thread_ts=thread_ts,
        )

    @mcp.tool
    @mcp_inject_client_id
    async def slack_list_dms(
        ctx: Context,
        client_id: str | None = None,
        limit: int = 20,
    ) -> dict:
        """
        Lista DMs (mensagens diretas) e grupos de mensagens (MPIMs) do Slack.

        Args:
            limit: Máximo de conversas a retornar (padrão 20)

        Returns:
            Dict com {total, dms: [{id, type, display_name, is_group}]}
        """
        return await _slack_list_dms_logic(client_id=client_id, limit=limit)

    @mcp.tool
    @mcp_inject_client_id
    async def slack_get_unread(
        ctx: Context,
        client_id: str | None = None,
        limit_per_channel: int = 5,
        max_channels: int = 10,
    ) -> dict:
        """
        Busca mensagens recentes da última hora em canais do Slack. IMs aparecem primeiro.

        Args:
            limit_per_channel: Máximo de mensagens por canal (padrão 5)
            max_channels: Máximo de canais a verificar (padrão 10)

        Returns:
            Dict com {channels: [{channel_id, channel_name, messages: [{user_name, text, ts}]}], total_messages}
        """
        return await _slack_get_unread_logic(
            client_id=client_id,
            limit_per_channel=limit_per_channel,
            max_channels=max_channels,
        )

    @mcp.tool
    @mcp_inject_client_id
    async def slack_search_messages(
        ctx: Context,
        query: str,
        client_id: str | None = None,
        count: int = 20,
        sort: str = "timestamp",
        sort_dir: str = "desc",
    ) -> dict:
        """
        Pesquisa mensagens no Slack por texto, usuário, canal ou data.

        Args:
            query: Termo de busca (suporta operadores Slack: from:, in:, before:, after:)
            count: Número de resultados (padrão 20)
            sort: Campo de ordenação — 'timestamp' ou 'score' (padrão 'timestamp')
            sort_dir: Direção — 'asc' ou 'desc' (padrão 'desc')

        Returns:
            Dict com {total, matches: [{text, channel_name, user, ts, permalink}]}
        """
        return await _slack_search_messages_logic(
            client_id=client_id,
            query=query,
            count=count,
            sort=sort,
            sort_dir=sort_dir,
        )

    @mcp.tool
    @mcp_inject_client_id
    async def slack_add_reaction(
        ctx: Context,
        channel_id: str,
        timestamp: str,
        emoji_name: str,
        client_id: str | None = None,
    ) -> dict:
        """
        Adiciona uma reação (emoji) a uma mensagem do Slack.

        Args:
            channel_id: ID do canal (ex: C01234567)
            timestamp: Timestamp da mensagem (ex: 1234567890.123456)
            emoji_name: Nome do emoji sem dois-pontos (ex: thumbsup, heart, white_check_mark)

        Returns:
            Dict com {ok, error} — error presente apenas se ok=False
        """
        return await _slack_add_reaction_logic(
            client_id=client_id,
            channel_id=channel_id,
            timestamp=timestamp,
            emoji_name=emoji_name,
        )

    @mcp.tool
    @mcp_inject_client_id
    async def slack_get_thread_replies(
        ctx: Context,
        channel_id: str,
        thread_ts: str,
        client_id: str | None = None,
        limit: int = 50,
    ) -> dict:
        """
        Busca as respostas de um thread do Slack.

        Args:
            channel_id: ID do canal (ex: C01234567)
            thread_ts: Timestamp do thread pai (ex: 1234567890.123456)
            limit: Máximo de mensagens a retornar (padrão 50)

        Returns:
            Dict com {parent: {user_name, text, ts}, replies: [{user_name, text, ts}], reply_count}
        """
        return await _slack_get_thread_replies_logic(
            client_id=client_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
            limit=limit,
        )

    return [
        "slack_list_channels",
        "slack_read_channel",
        "slack_summarize_channel",
        "slack_post_message",
        "slack_list_dms",
        "slack_get_unread",
        "slack_search_messages",
        "slack_add_reaction",
        "slack_get_thread_replies",
    ]
