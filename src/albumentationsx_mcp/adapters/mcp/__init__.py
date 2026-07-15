"""FastMCP registration adapters."""

from albumentationsx_mcp.adapters.mcp.contracts import AdapterSurface, CombinedSurface
from albumentationsx_mcp.adapters.mcp.dependencies import McpDependencies
from albumentationsx_mcp.adapters.mcp.registration import (
    ADAPTER_SURFACES,
    COMBINED_SURFACE,
    register_mcp_adapters,
)

__all__ = [
    "ADAPTER_SURFACES",
    "COMBINED_SURFACE",
    "AdapterSurface",
    "CombinedSurface",
    "McpDependencies",
    "register_mcp_adapters",
]
