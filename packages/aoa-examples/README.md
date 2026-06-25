<p align="center">
  <img src="../../docs/assets/aoa-logo.png" alt="AOA" width="660"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/version-1.0.0-informational" alt="1.0.0">
</p>

# aoa-examples: Reference Services for AOA

`aoa-examples` contains two runnable reference services — a FastAPI HTTP service and an MCP server — built on the same domain model: orders, products, and customers. Both services expose the same `Action` operations over different transports, demonstrating how a single piece of business logic is published via `FastApiAdapter` for REST clients and via `McpAdapter` for AI agents without duplicating any logic. The package also serves as the integration fixture used in the AOA test suite.
