"""Safe, configuration-scoped Azure VM operations."""

import logging
from typing import Any

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
    ServiceRequestError,
    ServiceResponseError,
)
from azure.identity import CredentialUnavailableError

from ..azure_vm import create_compute_client
from ..config import Settings

logger = logging.getLogger(__name__)


class VMServiceError(Exception):
    """User-safe service error with a category suitable for logs."""

    def __init__(self, message: str, category: str = "azure_error") -> None:
        super().__init__(message)
        self.category = category


class VMService:
    def __init__(self, config: Settings) -> None:
        self.config = config
        self.client = None

    def _get_client(self) -> Any:
        if self.client is None:
            try:
                self.config.validate()
                self.client = create_compute_client(self.config)
            except ValueError as exc:
                raise VMServiceError(str(exc), "configuration_error") from exc
            except (ClientAuthenticationError, CredentialUnavailableError) as exc:
                raise VMServiceError(
                    "Azure authentication failed. Run 'az login' or configure Managed Identity.",
                    "authentication_error",
                ) from exc
            except Exception as exc:
                raise VMServiceError("Unable to connect to Azure.", "connection_error") from exc
        return self.client

    def _log(self, action: str, result: str, category: str | None = None) -> None:
        logger.info(
            "vm_action timestamp=%s action=%s vm_name=%s result=%s error_category=%s",
            __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            action,
            self.config.vm_name,
            result,
            category or "none",
        )

    @staticmethod
    def _http_error_details(exc: HttpResponseError, action: str) -> tuple[str, str]:
        status_code = getattr(exc, "status_code", None)
        azure_error = getattr(exc, "error", None)
        error_code = str(getattr(azure_error, "code", "") or "").lower()
        error_message = str(getattr(azure_error, "message", "") or exc).lower()
        details = f"{error_code} {error_message}"

        if status_code in {401, 403}:
            return "authorization_error", "Azure denied this request. Check the signed-in identity and its VM permissions."
        if "subscription" in details or "invalidsubscription" in details:
            return "subscription_error", "The configured Azure subscription was not found or is not accessible."
        if "resourcegroup" in details or "resource group" in details:
            return "resource_group_not_found", "The configured Azure resource group was not found."
        if isinstance(exc, ResourceNotFoundError) or status_code == 404:
            return "vm_not_found", f"The configured Azure VM was not found in the resource group ({action} request)."
        return "azure_error", f"Azure could not complete the VM {action} request. Check the subscription, resource group, and VM name."

    @staticmethod
    def _status_from_instance_view(instance_view: Any) -> str:
        statuses = getattr(instance_view, "statuses", []) or []
        power_code = next(
            (
                status.code.lower()
                for status in statuses
                if getattr(status, "code", "").lower().startswith("powerstate/")
            ),
            "",
        )
        return {
            "powerstate/running": "VM running",
            "powerstate/stopped": "VM stopped",
            "powerstate/deallocated": "VM deallocated",
            "powerstate/starting": "VM starting",
            "powerstate/stopping": "VM stopping",
        }.get(power_code, power_code.replace("powerstate/", "VM ") if power_code else "VM status unavailable")

    def get_vm_status(self) -> str:
        try:
            client = self._get_client()
            view = client.virtual_machines.instance_view(
                self.config.resource_group, self.config.vm_name
            )
            status = self._status_from_instance_view(view)
            self._log("status", status)
            return status
        except VMServiceError:
            raise
        except (ClientAuthenticationError, CredentialUnavailableError) as exc:
            self._log("status", "failed", "authentication_error")
            raise VMServiceError(
                "Azure authentication failed. Run 'az login' or configure Managed Identity.",
                "authentication_error",
            ) from exc
        except HttpResponseError as exc:
            category, message = self._http_error_details(exc, "status")
            self._log("status", "failed", category)
            raise VMServiceError(message, category) from exc
        except (ServiceRequestError, ServiceResponseError) as exc:
            self._log("status", "failed", "network_error")
            raise VMServiceError("Unable to reach Azure. Check the network and try again.", "network_error") from exc
        except Exception as exc:
            self._log("status", "failed", "unexpected_error")
            raise VMServiceError("Azure could not return the VM status.", "unexpected_error") from exc

    def start_vm(self) -> str:
        return self._change_power_state("start")

    def stop_vm(self) -> str:
        return self._change_power_state("stop")

    def _change_power_state(self, action: str) -> str:
        try:
            client = self._get_client()
            view = client.virtual_machines.instance_view(
                self.config.resource_group, self.config.vm_name
            )
            current = self._status_from_instance_view(view)
            if action == "start" and current == "VM running":
                result = "VM is already running."
                self._log(action, result)
                return result
            if action == "stop" and current in {"VM stopped", "VM deallocated"}:
                result = "VM is already stopped or deallocated."
                self._log(action, result)
                return result

            operation = (
                client.virtual_machines.begin_start
                if action == "start"
                else client.virtual_machines.begin_deallocate
            )
            operation(self.config.resource_group, self.config.vm_name).result()
            result = f"VM {self.config.vm_name} {'started successfully' if action == 'start' else 'stopped successfully'}."
            self._log(action, result)
            return result
        except VMServiceError:
            raise
        except (ClientAuthenticationError, CredentialUnavailableError) as exc:
            self._log(action, "failed", "authentication_error")
            raise VMServiceError(
                "Azure authentication failed. Run 'az login' or configure Managed Identity.",
                "authentication_error",
            ) from exc
        except HttpResponseError as exc:
            category, message = self._http_error_details(exc, action)
            self._log(action, "failed", category)
            raise VMServiceError(message, category) from exc
        except (ServiceRequestError, ServiceResponseError) as exc:
            self._log(action, "failed", "network_error")
            raise VMServiceError("Unable to reach Azure. Check the network and try again.", "network_error") from exc
        except Exception as exc:
            self._log(action, "failed", "unexpected_error")
            raise VMServiceError("Azure could not complete the operation.", "unexpected_error") from exc
