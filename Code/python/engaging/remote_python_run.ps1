[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("package", "upload", "upload-submit", "submit", "status", "inventory", "fetch")]
  [string]$Action,
  [string]$RemoteHost = "USERNAME@orcd-login.mit.edu",
  [string]$RemoteDir = "~/state_pension_model_python",
  [string]$RunTag = "python_run",
  [string]$JobId = "",
  [string[]]$Plans = @("all"),
  [string[]]$UploadPlans = @("all"),
  [ValidateSet("detal", "asset", "both")]
  [string]$Stage = "both",
  [Alias("Parallel")]
  [int]$MaxParallel = 8,
  [int]$NumSim = 1000,
  [int]$PlanYear = 2022,
  [string]$TierFile = "planchanges_main_2022_clean.xlsx",
  [string]$DateRun = "",
  [string]$Seed = "",
  [string]$Partition = "",
  [string]$Account = "",
  [string]$Qos = "",
  [string]$PythonModule = "",
  [string]$PythonBin = "",
  [string]$CondaModule = "",
  [string]$CondaEnv = "",
  [string]$Venv = "",
  [switch]$Overwrite,
  [switch]$SkipExistingDetal,
  [switch]$SkipExistingAsset,
  [switch]$DryRun,
  [switch]$Follow
)

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$ClusterDir = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\.."))
$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $ClusterDir "..\.."))
$RemoteWorkDir = Join-Path $ProjectRoot "Results\Runs\$RunTag\_remote"
$LocalBundleWorkDir = Join-Path ([System.IO.Path]::GetTempPath()) "state_pension_model_python\$RunTag"
$UploadedPlanList = Join-Path $RemoteWorkDir "uploaded_plans.txt"
$Bundle = Join-Path $LocalBundleWorkDir "python_run_${RunTag}_bundle.tar.gz"
$BundleFileList = Join-Path $LocalBundleWorkDir "bundle_file_list.txt"
$RemoteBundleName = "python_run_${RunTag}_bundle.tar.gz"
$RemoteResultsName = "python_results_${RunTag}.tar.gz"
$SubmitScript = "Cluster Code/cluster_062026/Python Code/engaging/submit_slurm.sh"

function Require-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command not found on PATH: $Name"
  }
}

function Shell-Quote {
  param([string]$Value)
  if ($Value -match "^[A-Za-z0-9_./:@%+=,-]+$") {
    return $Value
  }
  return "'" + ($Value -replace "'", "'\''") + "'"
}

function Remote-Dir-Expr {
  if ($RemoteDir.StartsWith("~")) {
    return $RemoteDir
  }
  return Shell-Quote $RemoteDir
}

function Add-RelativeFile {
  param([System.Collections.Generic.List[string]]$List, [string]$Path)
  if (Test-Path -LiteralPath $Path) {
    $full = (Resolve-Path -LiteralPath $Path).Path
    $relative = $full.Substring($ProjectRoot.Length + 1) -replace "\\", "/"
    $List.Add($relative) | Out-Null
  }
}

function Add-RelativeDirectory {
  param([System.Collections.Generic.List[string]]$List, [string]$Path)
  if (Test-Path -LiteralPath $Path) {
    Get-ChildItem -LiteralPath $Path -Recurse -File | Where-Object {
      $_.FullName -notmatch "\\__pycache__\\" -and $_.Extension -ne ".pyc"
    } | ForEach-Object {
      $relative = $_.FullName.Substring($ProjectRoot.Length + 1) -replace "\\", "/"
      $List.Add($relative) | Out-Null
    }
  }
}

function Normalize-UnixTextFile {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    return
  }
  $text = [System.IO.File]::ReadAllText($Path)
  $text = $text -replace "`r`n", "`n"
  $text = $text -replace "`r", "`n"
  $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
  [System.IO.File]::WriteAllText($Path, $text, $utf8NoBom)
}

function Normalize-EngagingShellScripts {
  Get-ChildItem -LiteralPath (Join-Path $ClusterDir "Python Code\engaging") -Filter "*.sh" -File |
    ForEach-Object { Normalize-UnixTextFile $_.FullName }
}

function Get-CanonicalPlans {
  $planFile = Join-Path $ProjectRoot "Pipeline\062026\plans_38.txt"
  if (-not (Test-Path -LiteralPath $planFile)) {
    throw "Could not find canonical plan file: $planFile"
  }
  Get-Content -LiteralPath $planFile |
    Where-Object { $_ -and -not $_.Trim().StartsWith("#") } |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -ne "MA50" }
}

function Resolve-RequestedPlans {
  param([string[]]$Requested)
  $tokens = @()
  foreach ($entry in $Requested) {
    $tokens += ($entry -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
  }
  if ($tokens.Count -eq 0 -or $tokens -contains "all") {
    return @(Get-CanonicalPlans)
  }
  return @($tokens | Where-Object { $_ -ne "MA50" } | Select-Object -Unique)
}

function Write-UploadedPlanList {
  New-Item -ItemType Directory -Force -Path $RemoteWorkDir | Out-Null
  $selected = @(Resolve-RequestedPlans -Requested $UploadPlans)
  if ($selected.Count -lt 1) {
    throw "No upload plans selected."
  }
  [System.IO.File]::WriteAllText(
    $UploadedPlanList,
    (($selected -join "`n") + "`n"),
    [System.Text.Encoding]::ASCII
  )
  return $selected
}

function New-RunBundle {
  Require-Command tar
  Normalize-EngagingShellScripts
  New-Item -ItemType Directory -Force -Path $LocalBundleWorkDir | Out-Null
  $selected = @(Write-UploadedPlanList)

  $files = [System.Collections.Generic.List[string]]::new()
  Add-RelativeDirectory $files (Join-Path $ClusterDir "Python Code\engaging")
  foreach ($name in @(
      "Main_PensionModel.py",
      "asset_simulation.py",
      "bucketfill_cf_model.py",
      "functions_cf_model.py",
      "liability_cf_model.py",
      "g.py"
    )) {
    Add-RelativeFile $files (Join-Path $ClusterDir "Python Code\$name")
  }
  Add-RelativeDirectory $files (Join-Path $ClusterDir "Common_Data")
  Add-RelativeFile $files $UploadedPlanList

  foreach ($plan in $selected) {
    Add-RelativeFile $files (Join-Path $ProjectRoot "Plans\$plan\${plan}_2017.xlsx")
  }

  $files | Sort-Object -Unique | Set-Content -LiteralPath $BundleFileList -Encoding ASCII
  if (Test-Path -LiteralPath $Bundle) {
    Remove-Item -LiteralPath $Bundle -Force
  }

  Push-Location $ProjectRoot
  try {
    tar -czf $Bundle -T $BundleFileList
  } finally {
    Pop-Location
  }

  Write-Host "Bundle created: $Bundle"
  Write-Host "Uploaded list:  $UploadedPlanList"
  Write-Host "Uploaded plans: $($selected -join ', ')"
}

function Remote-Env-Prefix {
  $pairs = [System.Collections.Generic.List[string]]::new()
  $pairs.Add("RUN_TAG=$RunTag") | Out-Null
  $pairs.Add("STAGE=$Stage") | Out-Null
  $pairs.Add("MAX_PARALLEL=$MaxParallel") | Out-Null
  $pairs.Add("NUM_SIM=$NumSim") | Out-Null
  $pairs.Add("PLAN_YEAR=$PlanYear") | Out-Null
  $pairs.Add("TIER_FILE=$TierFile") | Out-Null
  $pairs.Add("PLANS=$(($Plans -join ','))") | Out-Null
  $pairs.Add('PROJECT_ROOT="$PWD"') | Out-Null
  $pairs.Add('PLAN_FILE="$PWD/Results/Runs/' + $RunTag + '/_remote/uploaded_plans.txt"') | Out-Null
  if ($DateRun) { $pairs.Add("DATE_RUN=$DateRun") | Out-Null }
  if ($Seed) { $pairs.Add("SEED=$Seed") | Out-Null }
  if ($Partition) { $pairs.Add("PARTITION=$Partition") | Out-Null }
  if ($Account) { $pairs.Add("ACCOUNT=$Account") | Out-Null }
  if ($Qos) { $pairs.Add("QOS=$Qos") | Out-Null }
  if ($PythonModule) { $pairs.Add("PYTHON_MODULE=$PythonModule") | Out-Null }
  if ($PythonBin) { $pairs.Add("PYTHON_BIN=$PythonBin") | Out-Null }
  if ($CondaModule) { $pairs.Add("CONDA_MODULE=$CondaModule") | Out-Null }
  if ($CondaEnv) { $pairs.Add("CONDA_ENV=$CondaEnv") | Out-Null }
  if ($Venv) { $pairs.Add("VENV=$Venv") | Out-Null }
  if ($Overwrite) { $pairs.Add("OVERWRITE=1") | Out-Null }
  if ($SkipExistingDetal) { $pairs.Add("SKIP_EXISTING_DETAL=1") | Out-Null }
  if ($SkipExistingAsset) { $pairs.Add("SKIP_EXISTING_ASSET=1") | Out-Null }
  if ($DryRun) { $pairs.Add("DRY_RUN=1") | Out-Null }

  ($pairs | ForEach-Object {
    if ($_ -like '*"$PWD*') {
      $_
    } else {
      $name, $value = $_ -split "=", 2
      "$name=$(Shell-Quote $value)"
    }
  }) -join " "
}

function Invoke-Upload {
  Require-Command ssh
  Require-Command scp
  New-RunBundle
  $rd = Remote-Dir-Expr
  & ssh $RemoteHost "mkdir -p $rd"
  & scp $Bundle "${RemoteHost}:${RemoteDir}/${RemoteBundleName}"
  & ssh $RemoteHost "cd $rd && tar -xzf ${RemoteBundleName}"
}

function Invoke-Submit {
  Require-Command ssh
  $rd = Remote-Dir-Expr
  $envPrefix = Remote-Env-Prefix
  $script = Shell-Quote $SubmitScript
  & ssh $RemoteHost "cd $rd && ${envPrefix} bash ${script}"
}

function Invoke-Fetch {
  Require-Command ssh
  Require-Command scp
  Require-Command tar
  New-Item -ItemType Directory -Force -Path $RemoteWorkDir | Out-Null
  $rd = Remote-Dir-Expr
  & ssh $RemoteHost "cd $rd && tar -czf ${RemoteResultsName} Results/Runs/${RunTag}"
  & scp "${RemoteHost}:${RemoteDir}/${RemoteResultsName}" $RemoteWorkDir
  Push-Location $ProjectRoot
  try {
    tar -xzf (Join-Path $RemoteWorkDir $RemoteResultsName)
  } finally {
    Pop-Location
  }
}

switch ($Action) {
  "package" {
    New-RunBundle
  }
  "upload" {
    Invoke-Upload
  }
  "upload-submit" {
    Invoke-Upload
    Invoke-Submit
  }
  "submit" {
    Invoke-Submit
  }
  "status" {
    Require-Command ssh
    if ($JobId) {
      & ssh $RemoteHost "squeue -j $(Shell-Quote $JobId) -o '%.18i %.12P %.30j %.8T %.10M %.6D %R'; sacct -j $(Shell-Quote $JobId) --format=JobID,JobName%30,State,ExitCode,Elapsed,Reason,NodeList"
    } else {
      & ssh $RemoteHost 'squeue --me; sacct -u "$USER" --format=JobID,JobName%30,State,ExitCode,Elapsed,Reason -S today'
    }
  }
  "inventory" {
    Require-Command ssh
    $rd = Remote-Dir-Expr
    $inventory = @"
set -euo pipefail
run_dir="Results/Runs/${RunTag}"
echo "remote: `$(pwd)"
echo "run: ${RunTag}"
echo
echo "deterministic pkl:"
find "`$run_dir" -mindepth 2 -maxdepth 2 -name "*_detAL_${RunTag}.pkl" | wc -l
echo "asset pkl:"
find "`$run_dir" -mindepth 2 -maxdepth 2 -name "*_AssetSim_2asset_${RunTag}.pkl" | wc -l
echo "parquet bundles:"
find "`$run_dir" -mindepth 2 -maxdepth 2 -type d -name "*_AssetSim_2asset_${RunTag}_parquet" | wc -l
"@
    $inventory | & ssh $RemoteHost "cd $rd && bash -s"
  }
  "fetch" {
    Invoke-Fetch
  }
}
