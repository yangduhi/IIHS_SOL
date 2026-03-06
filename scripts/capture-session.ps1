[CmdletBinding()]
param(
    [string]$Email = $env:IIHS_TECHDATA_EMAIL,
    [string]$Password = $env:IIHS_TECHDATA_PASSWORD,
    [string]$ProfileDir = ".auth\\profile",
    [string]$StorageState = ".auth\\storage-state.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Email) -or [string]::IsNullOrWhiteSpace($Password)) {
    throw "Set IIHS_TECHDATA_EMAIL and IIHS_TECHDATA_PASSWORD, or pass -Email and -Password."
}

$profileParent = Split-Path -Parent $ProfileDir
$stateParent = Split-Path -Parent $StorageState

if ($profileParent) {
    New-Item -ItemType Directory -Force $profileParent | Out-Null
}
if ($stateParent) {
    New-Item -ItemType Directory -Force $stateParent | Out-Null
}
New-Item -ItemType Directory -Force $ProfileDir | Out-Null
New-Item -ItemType Directory -Force "output\\playwright" | Out-Null

$env:IIHS_TECHDATA_EMAIL = $Email
$env:IIHS_TECHDATA_PASSWORD = $Password

& npx --yes --package @playwright/cli playwright-cli close-all | Out-Null
& npx --yes --package @playwright/cli playwright-cli open https://techdata.iihs.org/ --persistent --profile $ProfileDir | Out-Null

$loginCode = (
@'
async (page) => {
  await page.getByRole('link', { name: 'Log in to IIHS TechData' }).click();
  await page.getByRole('textbox', { name: 'User account' }).fill(process.env.IIHS_TECHDATA_EMAIL);
  await page.getByRole('textbox', { name: 'Password' }).fill(process.env.IIHS_TECHDATA_PASSWORD);
  const keepSignedIn = page.getByRole('checkbox', { name: 'Keep me signed in' });
  if (!(await keepSignedIn.isChecked())) {
    await keepSignedIn.check();
  }
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL(/https:\/\/techdata\.iihs\.org\/(?:default\.aspx)?$/);
  await page.waitForLoadState('networkidle');
  return { url: page.url(), title: await page.title() };
}
'@
) -replace '\r?\n', ' '

$assertCode = (
@'
async (page) => {
  const bodyText = await page.locator('body').innerText();
  if (!/downloads/i.test(bodyText) || !/sign out/i.test(bodyText)) {
    throw new Error('Login did not reach the authenticated home page.');
  }
  return { url: page.url(), title: await page.title() };
}
'@
) -replace '\r?\n', ' '

& npx --yes --package @playwright/cli playwright-cli run-code $loginCode | Out-Null
& npx --yes --package @playwright/cli playwright-cli run-code $assertCode | Out-Null

& npx --yes --package @playwright/cli playwright-cli state-save $StorageState | Out-Null
& npx --yes --package @playwright/cli playwright-cli snapshot --filename output\\playwright\\authenticated-home.md | Out-Null

Write-Host "Saved authenticated profile to $ProfileDir"
Write-Host "Saved storage state to $StorageState"
