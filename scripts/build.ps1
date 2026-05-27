# Package the FastAPI app + dependencies into a Lambda-ready zip.
# Run from repo root:  .\scripts\build.ps1
#
# Output: build/lambda.zip (target ~15-25 MB after stripping boto/pytest)
# That zip is referenced by terraform/variables.tf — var.lambda_zip_path defaults
# to "build/lambda.zip" relative to the terraform/ folder (i.e. ../build/lambda.zip
# from the repo root). Adjust the tfvars if you change this layout.

$ErrorActionPreference = "Stop"

$RepoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AppDir     = Join-Path $RepoRoot "app"
$BuildDir   = Join-Path $RepoRoot "build"
$ZipPath    = Join-Path $BuildDir "lambda.zip"
$StagingDir = Join-Path $BuildDir "lambda-staging"

Write-Host "==> Cleaning $BuildDir" -ForegroundColor Cyan
if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }
New-Item -ItemType Directory -Path $StagingDir | Out-Null

Write-Host "==> Installing Lambda-targeted dependencies (Python 3.12 manylinux)" -ForegroundColor Cyan
# We force manylinux wheels — Lambda runtime is Linux x86_64, NOT Windows.
# Without this, pydantic-core / pypdf may install Windows binaries that won't run on Lambda.
python -m pip install `
    --target $StagingDir `
    --platform manylinux2014_x86_64 `
    --implementation cp `
    --python-version 3.12 `
    --only-binary=:all: `
    --upgrade `
    -r (Join-Path $AppDir "requirements.txt") `
    mangum

if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install failed. A package may not have a manylinux wheel for cp312."
    exit 1
}

Write-Host "==> Copying app source" -ForegroundColor Cyan
Copy-Item -Path (Join-Path $AppDir "src") -Destination $StagingDir -Recurse
Copy-Item -Path (Join-Path $AppDir "lambda_handler.py") -Destination $StagingDir

Write-Host "==> Stripping bloat (boto3 + botocore are in Lambda runtime; pytest is dev-only)" -ForegroundColor Cyan
# Lambda Python 3.12 runtime ships with boto3 / botocore — bundling them again wastes 25+ MB.
$StripPkgs = @("boto3", "botocore", "pytest", "_pytest", "py", "pluggy", "iniconfig", "annotated_doc")
foreach ($pkg in $StripPkgs) {
    $path = Join-Path $StagingDir $pkg
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force
    }
}
# Strip matching .dist-info / .egg-info folders
Get-ChildItem -Path $StagingDir -Directory | Where-Object {
    $_.Name -match "^(boto3|botocore|pytest|py|pluggy|iniconfig|annotated_doc|_pytest)-.*\.(dist-info|egg-info)$"
} | ForEach-Object { Remove-Item $_.FullName -Recurse -Force }

# Strip __pycache__ + tests baggage from any package
Get-ChildItem -Path $StagingDir -Recurse -Directory | Where-Object {
    $_.Name -eq "__pycache__" -or $_.Name -eq "tests"
} | ForEach-Object { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }

Write-Host "==> Creating $ZipPath" -ForegroundColor Cyan
# PowerShell's Compress-Archive uses .NET ZipArchive — Lambda-compatible.
# Use Push-Location + relative paths so the archive entries don't carry the staging prefix.
Push-Location $StagingDir
try {
    Compress-Archive -Path "*" -DestinationPath $ZipPath -Force
} finally {
    Pop-Location
}

$ZipSizeMB = [Math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
Write-Host ""
Write-Host "==> Done. lambda.zip size: $ZipSizeMB MB" -ForegroundColor Green
Write-Host "    Path: $ZipPath"

if ($ZipSizeMB -gt 50) {
    Write-Warning "Zip > 50 MB direct-upload limit."
    Write-Warning "  Option A: upload zip to S3, set Lambda code from S3 in compute.tf"
    Write-Warning "  Option B: strip more deps (check $StagingDir before zipping)"
}
elseif ($ZipSizeMB -gt 250) {
    Write-Error "Zip > 250 MB — exceeds Lambda function size limit even unzipped."
}
