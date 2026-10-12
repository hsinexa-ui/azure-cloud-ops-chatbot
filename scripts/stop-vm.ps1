[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $SubscriptionId,
    [Parameter(Mandatory = $true)] [string] $ResourceGroupName,
    [Parameter(Mandatory = $true)] [string] $VMName
)

$ErrorActionPreference = 'Stop'
Connect-AzAccount | Out-Null
Set-AzContext -SubscriptionId $SubscriptionId | Out-Null
$vm = Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Status
$powerState = ($vm.Statuses | Where-Object Code -like 'PowerState/*' | Select-Object -First 1).DisplayStatus
Write-Host "$VMName current status: $powerState"
$confirmation = Read-Host "Type STOP to deallocate this VM"
if ($confirmation -ne 'STOP') {
    Write-Host 'Operation cancelled. The VM was not changed.'
    exit 0
}
Stop-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Force | Out-Null
$vm = Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Status
$powerState = ($vm.Statuses | Where-Object Code -like 'PowerState/*' | Select-Object -First 1).DisplayStatus
Write-Host "$VMName status after stop: $powerState"
