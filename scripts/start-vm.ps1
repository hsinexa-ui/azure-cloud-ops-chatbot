[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $SubscriptionId,
    [Parameter(Mandatory = $true)] [string] $ResourceGroupName,
    [Parameter(Mandatory = $true)] [string] $VMName
)

$ErrorActionPreference = 'Stop'
Connect-AzAccount | Out-Null
Set-AzContext -SubscriptionId $SubscriptionId | Out-Null
Start-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName | Out-Null
$vm = Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Status
$powerState = ($vm.Statuses | Where-Object Code -like 'PowerState/*' | Select-Object -First 1).DisplayStatus
Write-Host "$VMName status after start: $powerState"
