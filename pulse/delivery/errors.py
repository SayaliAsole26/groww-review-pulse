"""Delivery errors."""


class DeliveryError(RuntimeError):
    """Google Docs delivery via hosted MCP failed."""


class McpAuthError(DeliveryError):
    """Hosted MCP API key missing or rejected."""
