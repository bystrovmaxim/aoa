# Changelog

All notable changes to `maxitor-gnomon` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] – 2026-10-28

### Added

- **The Open Gnomon Protocol, versions 1.0 and 1.1** — a shared language for describing a project's model as a graph, one JSON Schema per version in `protocol/`; a published version never changes. ([#301](https://github.com/bystrovmaxim/aoa/issues/301))
- **`gnomon write` and `gnomon check`** — each service's model kept in one `graph.json`, rebuilt from the code and checked in CI; a stale file fails with its differences, matched by `id`. **`gnomon validate`** tells a graph from anything else; **`gnomon skill`** prints the setup skill. ([#301](https://github.com/bystrovmaxim/aoa/issues/301))
- **`gnomon.toml`**, the repository's list of graphs, with refusals that name the graph and the field. ([#301](https://github.com/bystrovmaxim/aoa/issues/301))
- **The `gnomon-setup` skill** — connects a project to the protocol: surveys every service, proves its export (adding an exporter where needed), asks, then writes the config, the graphs and the CI check; never commits. ([#301](https://github.com/bystrovmaxim/aoa/issues/301))
