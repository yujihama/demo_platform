param(
    [switch]$SkipDocker
)

Write-Host "[1/4] Playwright ブラウザをインストール中..."
python -m playwright install --with-deps

Write-Host "[2/4] E2E テスト依存関係をインストール中..."
python -m pip install -r tests/e2e/requirements.txt

$pytestArgs = @("tests/e2e", "--maxfail=1", "-s")
if ($SkipDocker) {
    $pytestArgs += @("-k", "not docker_compose")
}

Write-Host "[3/4] Playwright ブラウザ確認完了。"
Write-Host "[4/4] pytest を起動します: $pytestArgs"
python -m pytest @pytestArgs

