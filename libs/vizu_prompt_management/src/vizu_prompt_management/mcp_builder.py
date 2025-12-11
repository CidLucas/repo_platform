"""
MCP resource builder for prompts.

Provides integration with FastMCP for exposing prompts as MCP resources.
"""

import logging
from collections.abc import Callable
from typing import Any

from vizu_prompt_management.loader import PromptLoader
from vizu_prompt_management.templates import BUILTIN_TEMPLATES
from vizu_prompt_management.variables import VariableExtractor

logger = logging.getLogger(__name__)


class MCPPromptBuilder:
    """
    Build and register MCP prompt resources.

    Integrates with FastMCP to expose prompts as discoverable resources.
    """

    def __init__(
        self,
        mcp: Any,
        loader: PromptLoader | None = None,
        context_service_factory: Callable | None = None,
    ):
        """
        Initialize MCPPromptBuilder.

        Args:
            mcp: FastMCP instance
            loader: PromptLoader for database prompts
            context_service_factory: Factory for context service (for dynamic prompts)
        """
        self.mcp = mcp
        self.loader = loader or PromptLoader()
        self.context_service_factory = context_service_factory

    def register_standard_prompts(self) -> list[str]:
        """
        Register all standard built-in prompts with MCP.

        Returns:
            List of registered prompt names
        """
        registered = []

        for name, config in BUILTIN_TEMPLATES.items():
            self._register_builtin_prompt(name, config)
            registered.append(name)

        logger.info(f"Registered {len(registered)} standard MCP prompts")
        return registered

    def register_prompt(
        self,
        name: str,
        description: str | None = None,
        required_args: list[str] | None = None,
    ) -> None:
        """
        Register a single prompt with MCP.

        Args:
            name: Prompt name
            description: Optional description
            required_args: Optional list of required arguments
        """
        builtin = BUILTIN_TEMPLATES.get(name)

        if builtin:
            self._register_builtin_prompt(name, builtin)
        else:
            # Dynamic prompt from database
            self._register_dynamic_prompt(name, description, required_args)

    def _register_builtin_prompt(self, name: str, config) -> None:
        """Register a built-in prompt."""
        try:
            from fastmcp.prompts import Message

            # Build argument signature
            def make_prompt_fn(config):
                def prompt_fn(**kwargs) -> list:
                    prompt = self.loader.load_builtin(name, kwargs)
                    return [Message(role="system", content=prompt.content)]

                # Set function name and doc
                prompt_fn.__name__ = name.replace("/", "_").replace("-", "_")
                prompt_fn.__doc__ = config.description

                return prompt_fn

            prompt_fn = make_prompt_fn(config)

            # Register with MCP
            self.mcp.prompt(name)(prompt_fn)

        except ImportError:
            logger.warning("FastMCP not available for prompt registration")
        except Exception as e:
            logger.error(f"Error registering prompt {name}: {e}")

    def _register_dynamic_prompt(
        self,
        name: str,
        description: str | None,
        required_args: list[str] | None,
    ) -> None:
        """Register a dynamic prompt from database."""
        try:
            from fastmcp.prompts import Message

            loader = self.loader

            async def dynamic_prompt_fn(**kwargs) -> list:
                cliente_id = kwargs.pop("cliente_id", None)
                prompt = await loader.load(name, kwargs, cliente_id)
                return [Message(role="system", content=prompt.content)]

            dynamic_prompt_fn.__name__ = name.replace("/", "_").replace("-", "_")
            dynamic_prompt_fn.__doc__ = description or f"Dynamic prompt: {name}"

            self.mcp.prompt(name)(dynamic_prompt_fn)

        except ImportError:
            logger.warning("FastMCP not available for prompt registration")
        except Exception as e:
            logger.error(f"Error registering dynamic prompt {name}: {e}")

    def register_context_prompt(
        self,
        name: str,
        description: str = "Context-aware prompt",
    ) -> None:
        """
        Register a prompt that automatically loads client context.

        The prompt will accept `cliente_id` and auto-load variables.

        Args:
            name: Prompt name
            description: Prompt description
        """
        if not self.context_service_factory:
            logger.warning("Context service factory required for context prompts")
            return

        try:
            from fastmcp.prompts import Message

            loader = self.loader
            ctx_factory = self.context_service_factory

            async def context_prompt_fn(cliente_id: str, **kwargs) -> list:
                # Load context
                from uuid import UUID

                ctx_service = ctx_factory()
                context = await ctx_service.get_client_context_by_id(UUID(cliente_id))

                if not context:
                    return [
                        Message(
                            role="system",
                            content=f"⚠️ Cliente não encontrado: {cliente_id}",
                        )
                    ]

                # Extract variables from context
                variables = VariableExtractor.from_client_context(context)
                merged = {**variables.to_dict(), **kwargs}

                # Load prompt
                prompt = await loader.load(name, merged, UUID(cliente_id))
                return [Message(role="system", content=prompt.content)]

            context_prompt_fn.__name__ = name.replace("/", "_").replace("-", "_")
            context_prompt_fn.__doc__ = description

            self.mcp.prompt(name)(context_prompt_fn)

        except ImportError:
            logger.warning("FastMCP not available for prompt registration")
        except Exception as e:
            logger.error(f"Error registering context prompt {name}: {e}")

    def register_db_render(self) -> None:
        """
        Register the generic db/render prompt for dynamic rendering.

        This allows rendering any database prompt with custom variables.
        """
        try:
            import json

            from fastmcp.prompts import Message

            loader = self.loader

            def db_render_prompt(
                name: str,
                variables: str = "{}",
                version: str | None = None,
                cliente_id: str | None = None,
            ) -> list:
                """
                Render a prompt from the database with variables.

                Args:
                    name: Prompt name
                    variables: JSON string with variables
                    version: Optional specific version
                    cliente_id: Optional client ID

                Returns:
                    List of messages
                """
                try:
                    vars_dict = json.loads(variables) if variables else {}
                except json.JSONDecodeError:
                    vars_dict = {}

                version_int = int(version) if version else None
                cliente_uuid = None
                if cliente_id:
                    from uuid import UUID

                    try:
                        cliente_uuid = UUID(cliente_id)
                    except ValueError:
                        pass

                try:
                    # Use sync loading for MCP prompt
                    prompt = loader.load_builtin(name, vars_dict)
                    return [Message(role="system", content=prompt.content)]
                except Exception:
                    return [
                        Message(
                            role="system",
                            content=f"⚠️ Prompt '{name}' não encontrado.",
                        )
                    ]

            self.mcp.prompt("db/render")(db_render_prompt)
            logger.info("Registered db/render dynamic prompt")

        except ImportError:
            logger.warning("FastMCP not available")
        except Exception as e:
            logger.error(f"Error registering db/render: {e}")


def register_prompts_with_mcp(
    mcp: Any,
    db_session: Any | None = None,
    context_service_factory: Callable | None = None,
    prompts_to_register: list[str] | None = None,
) -> list[str]:
    """
    Convenience function to register prompts with an MCP server.

    Args:
        mcp: FastMCP instance
        db_session: Optional database session
        context_service_factory: Optional context service factory
        prompts_to_register: Optional list of specific prompts to register

    Returns:
        List of registered prompt names
    """
    loader = PromptLoader(db_session=db_session)
    builder = MCPPromptBuilder(
        mcp=mcp,
        loader=loader,
        context_service_factory=context_service_factory,
    )

    if prompts_to_register:
        for name in prompts_to_register:
            builder.register_prompt(name)
        builder.register_db_render()
        return prompts_to_register
    else:
        registered = builder.register_standard_prompts()
        builder.register_db_render()
        return registered
