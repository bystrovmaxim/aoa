# packages/maxitor/web/tests/test_history_version_file.py
"""What a port says about a history's version file reaches the reader, and a public link keeps its version file (spec 051)."""

from __future__ import annotations

from urllib.parse import parse_qs, quote, urlsplit

import pytest
from fastapi.testclient import TestClient
from maxitor.web.model.core.history_address import (
    HistoryAddressError,
    parse_history,
    parse_version_source,
    public_name,
    version_source,
)

from tests.fixtures.stand_in_port import PUBLIC_LINK, StandInPort
from tests.history_fixtures import maxitor, open_history, port  # noqa: F401 — fixtures

FILE_LINK = "https://github.com/owner/service/blob/main/pyproject.toml"
JOINED = f"{PUBLIC_LINK}?version_link={quote(FILE_LINK, safe='')}&version_key=project.version"


def poll(maxitor: TestClient, port: StandInPort, history: str) -> dict:  # noqa: F811
    """The answer a polling tab gets."""
    return maxitor.get("/api/history/versions", params={"history": port.name(history)}, headers={"X-Maxitor-History-Key": port.histories[history].key}).json()


def test_a_public_address_takes_only_its_version_file() -> None:
    """Both parameters are read and named in a fixed order; anything else is refused."""
    history = parse_history(f"{PUBLIC_LINK}?version_key=project.version&version_link={quote(FILE_LINK, safe='')}")
    assert history is not None and history.name == JOINED
    for address in (f"{PUBLIC_LINK}?x=1", f"{PUBLIC_LINK}?version_key=a", f"{PUBLIC_LINK}?version_link=a&version_link=b", f"{PUBLIC_LINK}?version_link="):
        with pytest.raises(HistoryAddressError):
            parse_history(address)


def test_a_versions_source_names_the_history_with_its_version_file() -> None:
    """A version's source comes back to the same name."""
    source = version_source("https://port/api/v1/history/public", PUBLIC_LINK, "a" * 12, FILE_LINK, "project.version")
    assert parse_version_source(source) == (JOINED, "a" * 12)
    assert public_name(PUBLIC_LINK, None, None) == PUBLIC_LINK


def test_the_port_hears_the_version_file_on_every_request(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """The description, the list and a version's graph all carry both parameters."""
    opened = maxitor.get("/api/history/open", params={"history": JOINED})
    assert opened.status_code == 200, opened.text
    assert opened.json()["name"] == JOINED
    read = maxitor.get("/api/v1/full-graph", params={"source": opened.json()["versions"][0]["source"]})
    assert read.status_code == 200, read.text
    public = [parse_qs(urlsplit(path).query) for path in port.requests if path.startswith("/api/v1/history/public")]
    assert len(public) >= 3
    assert all(query["version_link"] == [FILE_LINK] and query["version_key"] == ["project.version"] for query in public)


def test_one_graph_joined_with_two_files_is_two_histories(maxitor: TestClient) -> None:  # noqa: F811
    """Each holds its own version file."""
    plain = maxitor.get("/api/history/open", params={"history": PUBLIC_LINK}).json()
    joined = maxitor.get("/api/history/open", params={"history": JOINED}).json()
    assert plain["name"] != joined["name"]


def test_the_version_file_and_its_problem_reach_the_reader(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """Opening and polling both answer them."""
    history = port.histories["two"]
    history.version_file, history.version_problem = "version.toml", "The file holds no version."
    body = open_history(maxitor, port, "two").json()
    assert (body["version_file"], body["version_problem"]) == ("version.toml", "The file holds no version.")
    polled = poll(maxitor, port, "two")
    assert (polled["version_file"], polled["version_problem"]) == ("version.toml", "The file holds no version.")


def test_a_history_with_no_version_file_says_none(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """Both fields are empty."""
    body = open_history(maxitor, port, "two").json()
    assert body["version_file"] is None and body["version_problem"] is None


def test_the_fields_of_a_point_pass_as_the_port_sends_them(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """Nothing copies them away."""
    point = port.histories["two"].versions[-1]
    point.update(graph_changed=False, version="1.2.0", version_changed=True)
    newest = open_history(maxitor, port, "two").json()["versions"][-1]
    assert (newest["graph_changed"], newest["version"], newest["version_changed"]) == (False, "1.2.0", True)
