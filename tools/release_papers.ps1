[CmdletBinding()]
param(
    [string]$Repository = 'heming-666666/byd_transfer',
    [string]$ReleaseTag = 'papers-2026-09-22',
    [string]$ArchiveDirectory = '',
    [ValidateRange(500, 1900)]
    [int]$VolumeSizeMB = 1500,
    [string]$Proxy = 'http://127.0.0.1:7897',
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$paperRoot = Join-Path $root 'papers'
if (-not (Test-Path -LiteralPath $paperRoot -PathType Container)) {
    throw "Missing paper directory: $paperRoot"
}

if ([string]::IsNullOrWhiteSpace($ArchiveDirectory)) {
    $ArchiveDirectory = Join-Path (Split-Path $root -Parent) 'byd_release_work'
}
New-Item -ItemType Directory -Force -Path $ArchiveDirectory | Out-Null
$listDirectory = Join-Path $ArchiveDirectory 'lists'
New-Item -ItemType Directory -Force -Path $listDirectory | Out-Null
$snapshotPath = Join-Path $ArchiveDirectory "$ReleaseTag-snapshot.jsonl"

function Get-PaperEntries {
    $files = @(Get-ChildItem -LiteralPath $paperRoot -Recurse -Force -File -Filter '*.pdf' | Sort-Object FullName)
    if ($files.Count -eq 0) {
        throw "No PDF files found under $paperRoot"
    }

    $entries = foreach ($file in $files) {
        $relative = [IO.Path]::GetRelativePath($root, $file.FullName).Replace('\', '/')
        if ($relative -match '[\r\n]') {
            throw "Unsupported newline in path: $relative"
        }
        [pscustomobject]@{
            File = $file
            Relative = $relative
            Size = [int64]$file.Length
        }
    }
    return @($entries)
}

function Get-Batches([object[]]$Entries) {
    $limit = [int64]$VolumeSizeMB * 1MB
    $maxAssetBytes = [int64]2GB - 1MB
    $batches = @()
    $current = @()
    [int64]$currentBytes = 0

    foreach ($entry in $Entries) {
        if ($entry.Size -ge $maxAssetBytes) {
            throw "PDF is too large for a GitHub Release asset: $($entry.Relative) ($($entry.Size) bytes)"
        }
        if ($current.Count -gt 0 -and ($currentBytes + $entry.Size) -gt $limit) {
            $batches += ,@($current)
            $current = @()
            $currentBytes = 0
        }
        $current += ,$entry
        $currentBytes += $entry.Size
    }
    if ($current.Count -gt 0) {
        $batches += ,@($current)
    }
    return @($batches)
}

if (Test-Path -LiteralPath $snapshotPath -PathType Leaf) {
    $snapshotRows = @(Get-Content -LiteralPath $snapshotPath | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_ | ConvertFrom-Json })
    if ($snapshotRows.Count -eq 0) {
        throw "Paper snapshot is empty: $snapshotPath"
    }
    $entries = foreach ($row in $snapshotRows) {
        $relative = ([string]$row.Relative).Replace('/', '\')
        if ([IO.Path]::IsPathRooted($relative) -or -not $relative.StartsWith("papers\", [StringComparison]::OrdinalIgnoreCase)) {
            throw "Invalid path in paper snapshot: $($row.Relative)"
        }
        $filePath = Join-Path $root $relative
        if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
            throw "Snapshot file is missing: $($row.Relative)"
        }
        $file = Get-Item -LiteralPath $filePath
        $snapshotSize = [int64]$row.Size
        if ([int64]$file.Length -ne $snapshotSize) {
            throw "Snapshot file size changed: $($row.Relative)"
        }
        [pscustomobject]@{
            File = $file
            Relative = ([string]$row.Relative).Replace('\', '/')
            Size = $snapshotSize
        }
    }
    $entries = @($entries)
    Write-Host "Using paper snapshot: $snapshotPath"
} else {
    $entries = Get-PaperEntries
    $snapshotLines = foreach ($entry in $entries) {
        [pscustomobject]@{
            Relative = $entry.Relative
            Size = $entry.Size
        } | ConvertTo-Json -Compress
    }
    Set-Content -LiteralPath $snapshotPath -Value $snapshotLines -Encoding utf8NoBOM
    Write-Host "Created paper snapshot: $snapshotPath"
}
$batches = Get-Batches $entries
$partialFiles = @(Get-ChildItem -LiteralPath $paperRoot -Recurse -Force -File -Filter '*.part' -ErrorAction SilentlyContinue)
$totalBytes = ($entries | Measure-Object -Property Size -Sum).Sum
Write-Host ("PDFs: {0}; size: {1:N2} GiB; tar volumes: {2}; excluded .part files: {3}" -f $entries.Count, ($totalBytes / 1GB), $batches.Count, $partialFiles.Count)

if ($CheckOnly) {
    Write-Host 'CHECK_ONLY_OK'
    exit 0
}

function Get-GitHubToken {
    $credentialInput = "protocol=https`nhost=github.com`nusername=heming-666666`n`n"
    $credentialOutput = $credentialInput | git credential fill
    $passwordLine = $credentialOutput | Where-Object { $_ -like 'password=*' } | Select-Object -First 1
    if ($null -eq $passwordLine) {
        throw 'Git credential manager did not return a GitHub token'
    }
    return $passwordLine.Substring(9)
}

$token = Get-GitHubToken
$apiHeaders = @{
    Authorization = "Bearer $token"
    Accept = 'application/vnd.github+json'
    'X-GitHub-Api-Version' = '2022-11-28'
    'User-Agent' = 'byd-transfer-paper-release-uploader'
}

function Invoke-GitHubJson([string]$Method, [string]$Uri, [object]$Body = $null) {
    $params = @{
        Uri = $Uri
        Method = $Method
        Headers = $apiHeaders
        Proxy = $Proxy
        TimeoutSec = 120
        ErrorAction = 'Stop'
    }
    if ($null -ne $Body) {
        $params.Body = ($Body | ConvertTo-Json -Depth 10)
        $params.ContentType = 'application/json'
    }
    return Invoke-RestMethod @params
}

function Get-ReleaseAssets([int64]$ReleaseId) {
    $all = @()
    $page = 1
    do {
        $pageAssets = @(Invoke-GitHubJson 'GET' "https://api.github.com/repos/$Repository/releases/$ReleaseId/assets?per_page=100&page=$page")
        $all += $pageAssets
        $page++
    } while ($pageAssets.Count -eq 100)
    return @($all)
}

function Remove-ReleaseAsset([int64]$AssetId) {
    Invoke-GitHubJson 'DELETE' "https://api.github.com/repos/$Repository/releases/assets/$AssetId" | Out-Null
}

function Upload-ReleaseAsset([string]$Uri, [string]$Path) {
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.Proxy = [Net.WebProxy]::new($Proxy)
    $handler.UseProxy = $true
    $client = [Net.Http.HttpClient]::new($handler)
    $client.Timeout = [TimeSpan]::FromHours(2)
    $request = [Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::Post, $Uri)
    $fileStream = [IO.File]::OpenRead($Path)
    $content = [Net.Http.StreamContent]::new($fileStream)
    $response = $null
    try {
        $request.Headers.Authorization = [Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $token)
        $request.Headers.Accept.Add([Net.Http.Headers.MediaTypeWithQualityHeaderValue]::new('application/vnd.github+json'))
        $request.Headers.Add('X-GitHub-Api-Version', '2022-11-28')
        $request.Headers.UserAgent.ParseAdd('byd-transfer-paper-release-uploader')
        $content.Headers.ContentType = [Net.Http.Headers.MediaTypeHeaderValue]::new('application/octet-stream')
        $content.Headers.ContentLength = $fileStream.Length
        $request.Content = $content
        $response = $client.SendAsync($request, [Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
        $statusCode = [int]$response.StatusCode
        if ($statusCode -notin @(200, 201)) {
            $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            throw "HTTP ${statusCode}: $body"
        }
        return [string]$statusCode
    } finally {
        if ($null -ne $response) { $response.Dispose() }
        $request.Dispose()
        $content.Dispose()
        $fileStream.Dispose()
        $client.Dispose()
        $handler.Dispose()
    }
}

$release = $null
try {
    $encodedTag = [uri]::EscapeDataString($ReleaseTag)
    $release = Invoke-GitHubJson 'GET' "https://api.github.com/repos/$Repository/releases/tags/$encodedTag"
} catch {
    $statusCode = if ($null -ne $_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    if ($statusCode -ne 404) {
        throw
    }
}
if ($null -eq $release) {
    $releaseBody = @{
        tag_name = $ReleaseTag
        target_commitish = 'main'
        name = "BYD paper archives $ReleaseTag"
        body = "PDF archives for the local paper corpus. Download all papers-$ReleaseTag-*.tar assets and extract them from the repository root with: tar -xf <asset>. Incomplete .part downloads are excluded."
        draft = $false
        prerelease = $false
        generate_release_notes = $false
    }
    $release = Invoke-GitHubJson 'POST' "https://api.github.com/repos/$Repository/releases" $releaseBody
    Write-Host ("Created release: {0} ({1})" -f $release.html_url, $release.id)
} else {
    Write-Host ("Using existing release: {0} ({1})" -f $release.html_url, $release.id)
}

function Wait-ForUploadedAsset([string]$Name, [int64]$ExpectedSize, [int]$TimeoutSeconds = 900) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $remote = @(Get-ReleaseAssets $release.id | Where-Object { $_.name -eq $Name } | Select-Object -First 1)
        if ($remote.Count -eq 1 -and [string]$remote[0].state -eq 'uploaded' -and [int64]$remote[0].size -eq $ExpectedSize) {
            return $remote[0]
        }
        if ((Get-Date) -ge $deadline) {
            break
        }
        Start-Sleep -Seconds 15
    } while ($true)
    return $null
}

$assetMap = @{}
foreach ($asset in (Get-ReleaseAssets $release.id)) {
    $assetMap[$asset.name] = $asset
}

$archiveFiles = @()
for ($index = 0; $index -lt $batches.Count; $index++) {
    $number = $index + 1
    $baseName = "papers-$ReleaseTag-{0:D3}" -f $number
    $archivePath = Join-Path $ArchiveDirectory "$baseName.tar"
    $donePath = "$archivePath.done"
    $listPath = Join-Path $listDirectory "$baseName.txt"
    $batch = @($batches[$index])
    if (-not (Test-Path -LiteralPath $donePath -PathType Leaf)) {
        $batch | ForEach-Object { $_.Relative } | Set-Content -LiteralPath $listPath -Encoding utf8NoBOM
        if (Test-Path -LiteralPath $archivePath -PathType Leaf) {
            Write-Host "Validating existing archive $baseName"
            & tar.exe -tf $archivePath *> $null
            if ($LASTEXITCODE -ne 0) {
                throw "Existing incomplete archive cannot be validated: $archivePath; remove it manually and rerun"
            }
        } else {
            Write-Host ("Creating {0}/{1}: {2} PDFs" -f $number, $batches.Count, $batch.Count)
            & tar.exe -cf $archivePath -C $root -T $listPath
            if ($LASTEXITCODE -ne 0) {
                throw "tar failed for $archivePath with exit code $LASTEXITCODE"
            }
        }
        $archiveSize = (Get-Item -LiteralPath $archivePath).Length
        if ($archiveSize -ge ([int64]2GB - 1MB)) {
            throw "Archive exceeds the safe GitHub Release asset limit: $archivePath ($archiveSize bytes)"
        }
        Set-Content -LiteralPath $donePath -Value ("bytes={0}`nfiles={1}`n" -f $archiveSize, $batch.Count) -Encoding utf8NoBOM
    }

    $archive = Get-Item -LiteralPath $archivePath
    $archiveFiles += ,$archive
    $asset = $assetMap[$archive.Name]
    if ($null -ne $asset) {
        if ([string]$asset.state -eq 'uploaded' -and [int64]$asset.size -eq [int64]$archive.Length) {
            Write-Host ("Already uploaded {0} ({1:N2} GiB)" -f $archive.Name, ($archive.Length / 1GB))
            continue
        }
        if ([string]$asset.state -eq 'starter') {
            Write-Host "Removing unfinished remote asset $($archive.Name)"
            Remove-ReleaseAsset $asset.id
            $assetMap.Remove($archive.Name)
        } else {
            throw "Remote asset has a different size: $($archive.Name)"
        }
    }

    $uploadUri = "https://uploads.github.com/repos/$Repository/releases/$($release.id)/assets?name=$([uri]::EscapeDataString($archive.Name))"
    $uploaded = $false
    for ($attempt = 1; $attempt -le 4; $attempt++) {
        try {
            Write-Host ("Uploading {0}/{1}: {2:N2} GiB (attempt {3})" -f $number, $batches.Count, ($archive.Length / 1GB), $attempt)
            $uploadStatus = Upload-ReleaseAsset $uploadUri $archive.FullName
            if ($uploadStatus -notmatch '^(200|201)$') {
                throw "Upload returned HTTP $uploadStatus"
            }
            $remoteAfterUpload = @(Get-ReleaseAssets $release.id | Where-Object { $_.name -eq $archive.Name } | Select-Object -First 1)
            if ($remoteAfterUpload.Count -ne 1 -or [string]$remoteAfterUpload[0].state -ne 'uploaded' -or [int64]$remoteAfterUpload[0].size -ne [int64]$archive.Length) {
                throw "Remote asset is not fully uploaded yet: $($archive.Name)"
            }
            $uploaded = $true
            break
        } catch {
            $remoteAfterFailure = @(Get-ReleaseAssets $release.id | Where-Object { $_.name -eq $archive.Name } | Select-Object -First 1)
            if ($remoteAfterFailure.Count -gt 0) {
                $remoteAsset = $remoteAfterFailure[0]
            } else {
                $remoteAsset = $null
            }
            if ($null -ne $remoteAsset -and [string]$remoteAsset.state -eq 'uploaded' -and [int64]$remoteAsset.size -eq [int64]$archive.Length) {
                $uploaded = $true
                break
            }
            Write-Host "Waiting for GitHub to settle $($archive.Name)"
            $settled = Wait-ForUploadedAsset $archive.Name $archive.Length
            if ($null -ne $settled) {
                $uploaded = $true
                break
            }
            $remoteAfterWait = @(Get-ReleaseAssets $release.id | Where-Object { $_.name -eq $archive.Name } | Select-Object -First 1)
            if ($remoteAfterWait.Count -gt 0 -and [string]$remoteAfterWait[0].state -eq 'starter') {
                Remove-ReleaseAsset $remoteAfterWait[0].id
                $assetMap.Remove($archive.Name)
            }
            if ($attempt -eq 4) {
                throw "Upload failed for $($archive.Name): $($_.Exception.Message)"
            }
            Start-Sleep -Seconds (15 * $attempt)
        }
    }
    if (-not $uploaded) {
        throw "Upload did not complete for $($archive.Name)"
    }
    $assetMap[$archive.Name] = [pscustomobject]@{ name = $archive.Name; size = $archive.Length }
    Write-Host "Uploaded $($archive.Name)"
}

$finalAssets = Get-ReleaseAssets $release.id
$missing = foreach ($archive in $archiveFiles) {
    $remote = $finalAssets | Where-Object { $_.name -eq $archive.Name } | Select-Object -First 1
    if ($null -eq $remote -or [string]$remote.state -ne 'uploaded' -or [int64]$remote.size -ne [int64]$archive.Length) {
        $archive
    }
}
$missing = @($missing)
if ($missing.Count -ne 0) {
    throw "Release verification failed: $($missing.Count) archive assets are missing or have wrong sizes"
}
Write-Host ("RELEASE_UPLOAD_OK: {0} assets, {1:N2} GiB" -f $archiveFiles.Count, (($archiveFiles | Measure-Object -Property Length -Sum).Sum / 1GB))
