# VersionMessage


<p align="center">
  <a href="https://github.com/bystrovmaxim/aoa"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache-2.0"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white" alt="React 19"></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5.7-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="../../../../README.md"><img src="https://img.shields.io/badge/docs-Maxitor%20client-blue" alt="Maxitor client"></a>
</p>

**Role:** The chosen version's message under the track: its pull request's title and body, or its commit's message, as plain text whose only links are addresses and `#123`; at most nine lines, then it scrolls inside; Live's closing line instead of a message. (spec 037)

## Files

| File | Responsibility |
|------|----------------|
| `VersionMessage.tsx` | `messageOf` and the box, built from `linkify` parts as text nodes and anchors, never HTML. |
