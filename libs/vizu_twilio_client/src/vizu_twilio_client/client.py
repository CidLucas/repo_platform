"""Main Twilio client for conversation management, messaging, and phone operations."""

import logging
from typing import Any

from twilio.rest import Client

from vizu_twilio_client.config import TwilioSettings

logger = logging.getLogger(__name__)


class TwilioClient:
    """
    Comprehensive Twilio client for managing conversations, messages, and phone numbers.

    This client provides a high-level interface for:
    - Creating and managing conversations
    - Adding participants to conversations
    - Sending messages (SMS, WhatsApp, conversation messages)
    - Searching and purchasing phone numbers
    """

    def __init__(self, settings: TwilioSettings):
        """
        Initialize the Twilio client with settings.

        Args:
            settings: TwilioSettings instance with credentials
        """
        self.settings = settings
        self.client = Client(settings.account_sid, settings.auth_token)
        logger.info("TwilioClient initialized successfully")

    @classmethod
    def from_credentials(
        cls, account_sid: str, auth_token: str, **kwargs: Any
    ) -> "TwilioClient":
        """
        Create a TwilioClient from credentials directly.

        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            **kwargs: Additional settings (messaging_service_sid, default_from_number)

        Returns:
            Initialized TwilioClient instance
        """
        settings = TwilioSettings(
            account_sid=account_sid, auth_token=auth_token, **kwargs
        )
        return cls(settings)

    # ========================================================================
    # CONVERSATION MANAGEMENT
    # ========================================================================

    def create_conversation(
        self, friendly_name: str, unique_name: str | None = None
    ) -> str | None:
        """
        Create a new Twilio conversation.

        Args:
            friendly_name: Human-readable name for the conversation
            unique_name: Optional unique identifier for the conversation

        Returns:
            Conversation SID if successful, None otherwise
        """
        try:
            kwargs = {"friendly_name": friendly_name}
            if unique_name:
                kwargs["unique_name"] = unique_name

            conversation = self.client.conversations.v1.conversations.create(**kwargs)
            logger.info(
                f"Conversation '{friendly_name}' created successfully. SID: {conversation.sid}"
            )
            return conversation.sid
        except Exception as e:
            logger.error(f"Failed to create conversation '{friendly_name}': {e}")
            return None

    def get_conversation(self, conversation_sid: str) -> dict[str, Any] | None:
        """
        Get conversation details.

        Args:
            conversation_sid: Conversation SID

        Returns:
            Conversation details dict if found, None otherwise
        """
        try:
            conversation = self.client.conversations.v1.conversations(
                conversation_sid
            ).fetch()
            return {
                "sid": conversation.sid,
                "friendly_name": conversation.friendly_name,
                "unique_name": conversation.unique_name,
                "state": conversation.state,
                "date_created": conversation.date_created,
                "date_updated": conversation.date_updated,
            }
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_sid}: {e}")
            return None

    def delete_conversation(self, conversation_sid: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_sid: Conversation SID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            self.client.conversations.v1.conversations(conversation_sid).delete()
            logger.info(f"Conversation {conversation_sid} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_sid}: {e}")
            return False

    # ========================================================================
    # PARTICIPANT MANAGEMENT
    # ========================================================================

    def add_participant(
        self,
        conversation_sid: str,
        address: str,
        channel: str = "sms",
        proxy_address: str | None = None,
    ) -> str | None:
        """
        Add a participant to a conversation.

        Args:
            conversation_sid: Conversation SID
            address: Participant's phone number (e.g., '+1234567890')
            channel: Communication channel ('sms' or 'whatsapp')
            proxy_address: Optional proxy address (Twilio number to use)

        Returns:
            Participant SID if successful, None otherwise
        """
        try:
            # Format the messaging binding address
            if channel.lower() == "whatsapp":
                binding_address = f"whatsapp:{address}"
            else:
                binding_address = address

            kwargs: dict[str, Any] = {
                "messaging_binding_address": binding_address
            }

            if proxy_address:
                kwargs["messaging_binding_proxy_address"] = proxy_address

            participant = self.client.conversations.v1.conversations(
                conversation_sid
            ).participants.create(**kwargs)

            logger.info(
                f"Participant {address} ({channel}) added to conversation {conversation_sid}"
            )
            return participant.sid
        except Exception as e:
            logger.error(
                f"Failed to add participant {address} to conversation {conversation_sid}: {e}"
            )
            return None

    def remove_participant(
        self, conversation_sid: str, participant_sid: str
    ) -> bool:
        """
        Remove a participant from a conversation.

        Args:
            conversation_sid: Conversation SID
            participant_sid: Participant SID to remove

        Returns:
            True if removed successfully, False otherwise
        """
        try:
            self.client.conversations.v1.conversations(
                conversation_sid
            ).participants(participant_sid).delete()
            logger.info(
                f"Participant {participant_sid} removed from conversation {conversation_sid}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to remove participant {participant_sid} from conversation {conversation_sid}: {e}"
            )
            return False

    def list_participants(
        self, conversation_sid: str
    ) -> list[dict[str, Any]] | None:
        """
        List all participants in a conversation.

        Args:
            conversation_sid: Conversation SID

        Returns:
            List of participant details dicts, None on error
        """
        try:
            participants = self.client.conversations.v1.conversations(
                conversation_sid
            ).participants.list()

            return [
                {
                    "sid": p.sid,
                    "address": p.messaging_binding.get("address"),
                    "proxy_address": p.messaging_binding.get("proxy_address"),
                    "date_created": p.date_created,
                }
                for p in participants
            ]
        except Exception as e:
            logger.error(
                f"Failed to list participants for conversation {conversation_sid}: {e}"
            )
            return None

    # ========================================================================
    # MESSAGE SENDING
    # ========================================================================

    def send_conversation_message(
        self, conversation_sid: str, body: str, author: str = "system"
    ) -> str | None:
        """
        Send a message to a conversation.

        Args:
            conversation_sid: Conversation SID
            body: Message text
            author: Message author (default: 'system')

        Returns:
            Message SID if successful, None otherwise
        """
        try:
            message = self.client.conversations.v1.conversations(
                conversation_sid
            ).messages.create(author=author, body=body)
            logger.info(
                f"Message sent to conversation {conversation_sid}: '{body[:50]}...'"
            )
            return message.sid
        except Exception as e:
            logger.error(
                f"Failed to send message to conversation {conversation_sid}: {e}"
            )
            return None

    def send_sms(
        self,
        to: str,
        body: str,
        from_: str | None = None,
        media_url: list[str] | None = None,
    ) -> str | None:
        """
        Send an SMS message.

        Args:
            to: Recipient phone number
            body: Message text
            from_: Sender phone number (uses default if not provided)
            media_url: Optional list of media URLs for MMS

        Returns:
            Message SID if successful, None otherwise
        """
        try:
            sender = from_ or self.settings.default_from_number
            if not sender:
                logger.error("No from number provided and no default configured")
                return None

            kwargs: dict[str, Any] = {"to": to, "from_": sender, "body": body}
            if media_url:
                kwargs["media_url"] = media_url

            message = self.client.messages.create(**kwargs)
            logger.info(f"SMS sent to {to}: '{body[:50]}...'")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send SMS to {to}: {e}")
            return None

    def send_whatsapp(
        self, to: str, body: str, from_: str | None = None
    ) -> str | None:
        """
        Send a WhatsApp message.

        Args:
            to: Recipient phone number (without 'whatsapp:' prefix)
            body: Message text
            from_: Sender WhatsApp number (uses default if not provided)

        Returns:
            Message SID if successful, None otherwise
        """
        try:
            sender = from_ or self.settings.default_from_number
            if not sender:
                logger.error("No from number provided and no default configured")
                return None

            # Format numbers with whatsapp: prefix
            to_formatted = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
            from_formatted = (
                f"whatsapp:{sender}" if not sender.startswith("whatsapp:") else sender
            )

            message = self.client.messages.create(
                to=to_formatted, from_=from_formatted, body=body
            )
            logger.info(f"WhatsApp message sent to {to}: '{body[:50]}...'")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message to {to}: {e}")
            return None

    # ========================================================================
    # PHONE NUMBER OPERATIONS
    # ========================================================================

    def search_available_phone_numbers(
        self,
        country_code: str = "US",
        area_code: str | None = None,
        contains: str | None = None,
        sms_enabled: bool = True,
        mms_enabled: bool = False,
        voice_enabled: bool = False,
        limit: int = 10,
    ) -> list[dict[str, Any]] | None:
        """
        Search for available phone numbers.

        Args:
            country_code: Two-letter country code (default: 'US')
            area_code: Optional area code filter
            contains: Optional pattern the number should contain
            sms_enabled: Filter for SMS capability
            mms_enabled: Filter for MMS capability
            voice_enabled: Filter for voice capability
            limit: Maximum number of results

        Returns:
            List of available phone numbers with details, None on error
        """
        try:
            kwargs: dict[str, Any] = {"limit": limit}
            if area_code:
                kwargs["area_code"] = area_code
            if contains:
                kwargs["contains"] = contains
            if sms_enabled:
                kwargs["sms_enabled"] = True
            if mms_enabled:
                kwargs["mms_enabled"] = True
            if voice_enabled:
                kwargs["voice_enabled"] = True

            numbers = (
                self.client.available_phone_numbers(country_code)
                .local.list(**kwargs)
            )

            results = [
                {
                    "phone_number": num.phone_number,
                    "friendly_name": num.friendly_name,
                    "capabilities": {
                        "sms": num.capabilities.get("sms", False),
                        "mms": num.capabilities.get("mms", False),
                        "voice": num.capabilities.get("voice", False),
                    },
                    "locality": num.locality,
                    "region": num.region,
                    "postal_code": num.postal_code,
                }
                for num in numbers
            ]

            logger.info(f"Found {len(results)} available phone numbers in {country_code}")
            return results
        except Exception as e:
            logger.error(
                f"Failed to search available phone numbers in {country_code}: {e}"
            )
            return None

    def buy_phone_number(
        self,
        phone_number: str,
        friendly_name: str | None = None,
        sms_url: str | None = None,
        voice_url: str | None = None,
        status_callback: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Purchase a phone number.

        Args:
            phone_number: Phone number to purchase (e.g., '+14155551234')
            friendly_name: Optional friendly name for the number
            sms_url: Optional webhook URL for incoming SMS
            voice_url: Optional webhook URL for incoming calls
            status_callback: Optional webhook URL for status updates

        Returns:
            Purchased number details dict if successful, None otherwise
        """
        try:
            kwargs: dict[str, Any] = {"phone_number": phone_number}
            if friendly_name:
                kwargs["friendly_name"] = friendly_name
            if sms_url:
                kwargs["sms_url"] = sms_url
            if voice_url:
                kwargs["voice_url"] = voice_url
            if status_callback:
                kwargs["status_callback"] = status_callback

            number = self.client.incoming_phone_numbers.create(**kwargs)

            result = {
                "sid": number.sid,
                "phone_number": number.phone_number,
                "friendly_name": number.friendly_name,
                "capabilities": {
                    "sms": number.capabilities.get("sms", False),
                    "mms": number.capabilities.get("mms", False),
                    "voice": number.capabilities.get("voice", False),
                },
            }

            logger.info(f"Successfully purchased phone number: {phone_number}")
            return result
        except Exception as e:
            logger.error(f"Failed to purchase phone number {phone_number}: {e}")
            return None

    def update_phone_number(
        self,
        phone_number_sid: str,
        friendly_name: str | None = None,
        sms_url: str | None = None,
        voice_url: str | None = None,
    ) -> bool:
        """
        Update configuration for an owned phone number.

        Args:
            phone_number_sid: Phone number SID
            friendly_name: New friendly name
            sms_url: New SMS webhook URL
            voice_url: New voice webhook URL

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            kwargs: dict[str, Any] = {}
            if friendly_name is not None:
                kwargs["friendly_name"] = friendly_name
            if sms_url is not None:
                kwargs["sms_url"] = sms_url
            if voice_url is not None:
                kwargs["voice_url"] = voice_url

            if not kwargs:
                logger.warning("No update parameters provided")
                return False

            self.client.incoming_phone_numbers(phone_number_sid).update(**kwargs)
            logger.info(f"Phone number {phone_number_sid} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to update phone number {phone_number_sid}: {e}")
            return False

    def release_phone_number(self, phone_number_sid: str) -> bool:
        """
        Release (delete) an owned phone number.

        Args:
            phone_number_sid: Phone number SID to release

        Returns:
            True if released successfully, False otherwise
        """
        try:
            self.client.incoming_phone_numbers(phone_number_sid).delete()
            logger.info(f"Phone number {phone_number_sid} released successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to release phone number {phone_number_sid}: {e}")
            return False
