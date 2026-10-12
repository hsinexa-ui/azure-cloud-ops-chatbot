"""Azure credential and Compute Management client factory."""

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

from .config import Settings


def create_compute_client(config: Settings) -> ComputeManagementClient:
    """Create a client using Azure CLI locally or Managed Identity in Azure."""
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return ComputeManagementClient(credential, config.subscription_id)
