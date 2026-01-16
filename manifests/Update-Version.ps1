param (
    [string]$filePath,
    [string]$oldVersion,
    [string]$newVersion
)

if (-Not (Test-Path $filePath)) {
    Write-Error "File not found: $filePath"
    exit 1
}

try {
    $content = Get-Content -Path $filePath
    $newContent = $content -replace "version: $oldVersion", "version: $newVersion"
    $newContent = $newContent -replace "image: (.*):$oldVersion", "image: `$1:$newVersion"


    Set-Content -Path $filePath -Value $newContent
    Write-Output "Version updated successfully to $newVersion in file $filePath"
} catch {
    Write-Error "An error occurred: $_"
}