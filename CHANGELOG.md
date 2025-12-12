# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-12-12

### Fixed
- Fixed download async requests not disabling SSL verification when `SSL_ENABLED` is set to `false`

## [1.0.0] - 2025-12-05

### Added
- Initial GA (General Availability) release
- IBM Content Services MCP Server implementation
- GraphQL client for Content Services integration
- Document management tools (create, update, delete, download)
- Folder management tools (create, update, delete, list)
- Search capabilities (basic)
- Class and annotation management
- SSL/TLS support with configurable verification

[1.0.1]: https://github.com/ibm/ibm-content-services-mcp-server/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/ibm/ibm-content-services-mcp-server/releases/tag/v1.0.0