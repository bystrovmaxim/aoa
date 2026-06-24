<p align="center">
  <img src="../../docs/assets/aoa-logo.png" alt="AOA" width="660"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/version-1.0.0-informational" alt="1.0.0">
</p>

# aoa-langgraph-adapter: Use AOA Actions as LangGraph Nodes

`aoa-langgraph-adapter` bridges AOA and LangGraph: each `Action` becomes a typed LangGraph node that the graph can invoke by passing `Params` and receiving a `Result`. The adapter wraps the full AOA execution path — pipeline, compensations, plugins, role checks — so the orchestration logic stays in LangGraph while all business rules remain in `Action`. A single operation can serve HTTP via `FastApiAdapter`, tools via `McpAdapter`, and a LangGraph agent simultaneously, with no duplication.
