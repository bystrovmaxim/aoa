<p align="center">
  <img src="../../docs/assets/aoa-logo.png" alt="AOA" width="660"><br><br>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <a href="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml"><img src="https://github.com/bystrovmaxim/aoa/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/version-1.0.0-informational" alt="1.0.0">
</p>

# aoa-otel: OpenTelemetry Plugin for AOA

`aoa-otel` ships `OpenTelemetryPlugin` — a drop-in plugin that instruments every `Action` run with OpenTelemetry spans and structured log records. Attach it to `ActionProductMachine` and each operation automatically emits a root span for the full run, child spans for every pipeline aspect, and a span for each compensation — carrying `params`, the full `state` snapshot, timing, and error details as span attributes. No changes to business code required: observation is handled entirely at the plugin boundary, leaving `Action` logic untouched.
