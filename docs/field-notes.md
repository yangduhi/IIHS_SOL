# IIHS TechData Field Notes

## 2026-03-06 Authenticated Session

- Login was successful through the Microsoft `iihspublic.onmicrosoft.com` flow.
- The authenticated top nav exposes:
  - `RSS`
  - `downloads`
  - `my account`
  - `sign out`
- The RSS endpoint is `https://techdata.iihs.org/rss.ashx`.
- The downloads page is `https://techdata.iihs.org/secure/filegroups.aspx`.
- Selecting a test type in the dropdown is not enough by itself during automation. The `Submit` button must be clicked to refresh results.

## Confirmed Small Overlap Routes

- Driver-side:
  - `https://techdata.iihs.org/secure/filegroups.aspx?t=25&r=released`
- Passenger-side:
  - `https://techdata.iihs.org/secure/filegroups.aspx?t=26&r=released`

## Confirmed Type Codes

- `25` = `Small overlap frontal: driver-side`
- `26` = `Small overlap frontal: passenger-side`

## Observed Pagination On 2026-03-06

- Driver-side list pages: `15`
- Passenger-side list pages: `3`

## Confirmed Detail-Page Behavior

- Example passenger-side detail page:
  - `https://techdata.iihs.org/secure/filegroup.aspx?2589`
- Folder selection uses ASP.NET postback links of the form:
  - `javascript:__doPostBack('ctl00$MainContentPlaceholder$FileBrowser$FolderList$...','')`
- File downloads are rendered as direct links under:
  - `/secure/file.ashx?...`

## Confirmed Download Behavior

- Unauthenticated `HEAD` request to an example `/secure/file.ashx?...` URL returned `302` and redirected to `/`.
- Authenticated browser-context `fetch()` to the same file URL returned:
  - status: `200`
  - content type: `image/jpeg`
  - content disposition: `inline; filename=CN15007#01_w.jpg`
  - size: `86333` bytes

## Example Folder Tree For Filegroup 2589

- `Root`
- `DATA\DAS`
- `DATA\DIAdem`
- `DATA\EDR`
- `DATA\EXCEL`
- `PHOTOS`
- `REPORTS`
- `VIDEO`

## Example File Pagination

- `PHOTOS` in filegroup `2589` showed `9` pages.
