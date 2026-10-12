# Azure VM Control Chatbot

A beginner-friendly FastAPI chatbot for checking, starting, and safely deallocating one preconfigured Azure VM. It is designed for an authorized operator of a D365 Finance & Operations development or test environment.

> Stopping an Azure VM is an infrastructure operation. It is not automatically equivalent to stopping, pausing, or changing a D365 Finance & Operations / Lifecycle Services (LCS) environment. Production D365 environments are intentionally outside this project's scope.

## Project Overview

The chatbot accepts simple natural-language requests:

- `What is the VM status?`
- `Start my DEV VM`
- `Stop my DEV VM`

A stop request creates a confirmation step. The backend controls only the VM configured by environment variables, never a VM name supplied in chat.

## Architecture

- `frontend/`: static HTML, CSS, and JavaScript client.
- `backend/main.py`: FastAPI routes and the small command processor.
- `backend/config.py`: environment-only configuration and DEV/TEST safety checks.
- `backend/azure_vm.py`: `DefaultAzureCredential` and Azure client factory.
- `backend/services/vm_service.py`: status, start, and deallocate operations with safe error mapping.
- `scripts/`: separate, human-invoked Az PowerShell learning/admin scripts.
- `tests/`: mocked API tests. They never call Azure.

## Prerequisites

- Windows 10/11 or another supported Python platform.
- Python 3.11 or newer.
- Visual Studio Code or Visual Studio with Python support.
- An Azure subscription and an existing VM in a DEV or TEST resource group.
- Azure CLI for local login.
- Optional: Azure PowerShell `Az` module for the scripts.

Install Python from https://www.python.org/downloads/ and confirm:

```powershell
python --version
```

Install Azure CLI from https://learn.microsoft.com/cli/azure/install-azure-cli-windows and confirm:

```powershell
az version
```

Optional PowerShell module:

```powershell
Install-Module -Name Az -Scope CurrentUser
```

## Setup

From the `azure-vm-chatbot` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with the subscription ID, resource group, and VM name. Do not commit `.env`; it is ignored by Git. Do not put credentials, tokens, passwords, or client secrets in it.

For local authentication:

```powershell
az login
az account list --output table
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

The application uses `DefaultAzureCredential`. Locally it can use the Azure CLI credential created by `az login`. It does not store a username or password.

## Azure VM Information

Use the Azure portal, CLI, or PowerShell to find the exact values:

```powershell
az vm list --output table
az vm show --resource-group D365-DEV-RG --name D365DEVVM01 --show-details --output table
```

Set these values in `.env`:

```text
AZURE_SUBSCRIPTION_ID=...
AZURE_RESOURCE_GROUP=D365-DEV-RG
AZURE_VM_NAME=D365DEVVM01
AZURE_ENVIRONMENT=DEV
ALLOWED_ENVIRONMENTS=DEV,TEST
FRONTEND_ORIGIN=http://localhost:5500
```

The default environment is `DEV`. The configuration rejects environments outside the explicit DEV/TEST allowlist and rejects production control.

## Required Azure RBAC Permissions

Grant the signed-in developer or production Managed Identity the least privilege needed on the specific VM or resource group:

- `Microsoft.Compute/virtualMachines/read`
- `Microsoft.Compute/virtualMachines/start/action`
- `Microsoft.Compute/virtualMachines/deallocate/action`

The built-in **Virtual Machine Contributor** role includes these VM management actions but also grants broader VM permissions. Prefer a narrowly scoped custom role when your organization's policy requires least privilege. Do not grant Owner or Contributor just to make this sample work.

## Start the Backend

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --port 8000
```

Backend URLs:

- API root: http://localhost:8000/
- Health: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

## Start the Frontend

Keep the backend running, open a second terminal, and run:

```powershell
python -m http.server 5500 --directory frontend
```

Open http://localhost:5500. The frontend defaults to `http://localhost:8000` for the API. The backend CORS origin defaults to `http://localhost:5500`.

## API Testing

Health:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Status:

```powershell
Invoke-RestMethod http://localhost:8000/vm/status
```

Start:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/vm/start
```

Stop without confirmation returns a confirmation response:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/vm/stop -ContentType 'application/json' -Body '{"confirmed":false}'
```

Stop with confirmation:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/vm/stop -ContentType 'application/json' -Body '{"confirmed":true}'
```

Chat examples:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -ContentType 'application/json' -Body '{"message":"What is the VM status?"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -ContentType 'application/json' -Body '{"message":"Stop my DEV VM"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/chat -ContentType 'application/json' -Body '{"message":"Yes"}'
```

Swagger UI at `/docs` provides an interactive way to test every route.

## PowerShell Usage

These scripts are separate from the chatbot and accept only explicit parameters. They never accept arbitrary commands from chat.

```powershell
.\scripts\check-vm.ps1 -SubscriptionId 'YOUR_SUBSCRIPTION_ID' -ResourceGroupName 'D365-DEV-RG' -VMName 'D365DEVVM01'
.\scripts\start-vm.ps1 -SubscriptionId 'YOUR_SUBSCRIPTION_ID' -ResourceGroupName 'D365-DEV-RG' -VMName 'D365DEVVM01'
.\scripts\stop-vm.ps1 -SubscriptionId 'YOUR_SUBSCRIPTION_ID' -ResourceGroupName 'D365-DEV-RG' -VMName 'D365DEVVM01'
```

Each script calls `Connect-AzAccount`, selects the subscription, and verifies the resulting power state. The stop script requires typing `STOP`.

## Tests

The test dependencies are included in `requirements.txt`. From the repository root, install dependencies and run the checks with:

```powershell
python -m pip install -r requirements.txt
python -m compileall -q backend tests
python -m pytest -q
```

The suite mocks the VM service and cannot start or stop a real VM. It covers health, status, start, stop confirmation, cancellation, invalid commands, and safe error responses. The compile check catches Python syntax errors, and running pytest also verifies that the test and application imports work.

## GitHub Actions CI

The CI workflow in `.github/workflows/ci.yml` runs on pushes and pull requests targeting `main`. It uses Python 3.11, caches pip downloads, checks Python syntax, and runs the pytest suite. The workflow requires no Azure credentials and does not perform Azure operations; API tests replace the VM service with a fake.

To verify CI on GitHub, push a branch and open a pull request targeting `main`, or push directly to `main`. Open the repository's **Actions** tab and check the **CI** workflow run. No repository secrets or Azure-specific workflow configuration are required.

## Troubleshooting

**Authentication failed:** run `az login`, select the right tenant and subscription, then restart the backend. In Azure, verify Managed Identity is enabled and has the required RBAC actions.

**Permission denied:** assign the least-privilege VM role at the VM or resource-group scope and wait for RBAC propagation.

**VM not found:** verify all three values in `.env` exactly, including subscription, resource group, and VM name.

**Frontend cannot reach the API:** confirm port 8000 is running, serve the frontend on port 5500, and ensure `FRONTEND_ORIGIN` matches the browser origin.

**Already running/stopped:** the service reports the current state and avoids unnecessary Azure operations.

**Timeout or network failure:** check connectivity, Azure service health, and retry. The API returns a safe message without stack traces or credentials.

## Security Considerations

- Keep `.env` private and never commit it.
- Use Azure CLI authentication locally and Managed Identity in Azure-hosted production deployments.
- Scope RBAC to the smallest resource possible.
- Keep the application behind appropriate identity-aware access control, private networking, or an authenticated gateway before exposing it beyond localhost.
- Review logs for actions and outcomes; this project never logs tokens or secrets.
- Keep the allowlist limited to DEV/TEST and do not configure production VMs.
- Never add arbitrary PowerShell execution to the chat endpoint.
- The in-memory pending confirmation is intended for a single trusted local operator. A multi-user deployment should bind pending confirmations to an authenticated user/session and use a shared, expiring store.

## Production Deployment and Managed Identity

Deploy the backend to an Azure service that supports a system-assigned or user-assigned Managed Identity, such as App Service, Container Apps, or a VM. Enable the identity, grant it the required VM RBAC actions, set the three `AZURE_*` resource variables as deployment configuration, and keep `AZURE_ENVIRONMENT=DEV` or `TEST`. `DefaultAzureCredential` will use the Managed Identity automatically in Azure and will not require a client secret.

Before any production rollout, add real user authentication and authorization, audit retention, rate limits, CSRF protections appropriate to the hosting model, and an approval workflow. Do not use this sample to automatically shut down production D365 environments or to claim LCS lifecycle control.
