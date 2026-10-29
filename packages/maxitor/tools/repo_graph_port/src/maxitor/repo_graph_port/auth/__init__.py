# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/auth/__init__.py
"""
The read keys' authentication — who a request reads as, from the key it carries.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

AOA's auth pipeline for the port: the key is taken from its header, hashed and
found in the histories config, and the request reads as that key's holder, with
the one history the key opens; a request with no key, or a key that opens nothing,
reads as a guest, who can open only public links.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

request ──extractor──► key ──authenticator──► HistoryReaderInfo | None ──coordinator──► HistoryContext.
"""
