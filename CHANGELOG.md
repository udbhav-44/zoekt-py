# Changelog

All notable changes to this project will be documented here.

The format is based on Keep a Changelog
and this project adheres to Semantic Versioning.

## [0.2.0] - 2025-12-28
### Added

## Released

### Fixed
- Fixed setup error caused by multiple entry points by excluding `assets/`.  
  (`7fa3dc0614a129ecc9d838dd18fa4619856ad7f7`)
- Added missing `requests` dependency required for pytest.  
  (`027a96a2edb2b215420244760b9144c8ba81c1f7`)
- Fixed setup error related to the license file attribute.  
  (`701e95055f617426ce0f1697c0aa861fa263a3a9`)
- Fixed the `list` command.  
  (`322ebad`)

### Changed
- Added default values to CLI flags in the help text to improve clarity without requiring source inspection.  
  (`a81947355c156284a93369e802e8f5483b8f3da8`)
- Separated repository name and filename output to improve ctrl-click behavior in editors like VS Code and Zed.  
  (`1a4c0cb643363f3bad123b562a39dc2057ff7bbd`)
- Included the first match line number in the filename output to enable direct editor navigation.  
  (`511a72c`)
- Renamed the installed script from `zoekt` to `zoekt-py` to avoid conflicts with the official Zoekt client binary.  
  (`6d3677ffbda5191b6f65868dc6cc20e24ac36a43`)

### Added
- Added `--theme` flag to select Rich syntax highlighting themes. Defaults to `ansi_light` to match common terminal color schemes.  
  (`3f641411c48a1ce3a8a63c38e41b0560a0e04cf7`)
- Embedded remote repository and file URLs into filename headers by default. Can be disabled with `--no-links`.  
  (`0d83a8261caab758bd7fac398ed18a31a3bd06aa`)
- Added search result match highlighting by default. Can be disabled with `--no-highlight-matches`.  
  (`ae0eddc69879d0e780cd94b41aa45ff7154dcf8f`)
- Added `--color` flag to force color output even when piping output, for example into `less`.  
  (`dbdae981d74a8ccb9c70300c18a80b5afe3ac4cd`)
- Added pagination support enabled by default. Can be disabled with `--no-pager`. Note that when mouse support is enabled in the pager, links require ctrl-shift-click to open.  
  (`322ebad`)

### Credits
- Thanks to **@H3mul** for the initial batch of fixes, UX improvements, and feature additions.
