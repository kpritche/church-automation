from __future__ import annotations

from bulletins_app.make_bulletins import _fetch_people_names_from_list, _get_people_lists_index


class FakePCO:
    def __init__(self, responses: dict[str, list[dict]]) -> None:
        self._responses = responses

    def iterate(self, endpoint: str):
        yield from self._responses.get(endpoint, [])


def test_get_people_lists_index_unwraps_iterate_responses() -> None:
    pco = FakePCO(
        {
            "/people/v2/lists": [
                {
                    "data": {
                        "id": "4742806",
                        "attributes": {"name": "Active Military"},
                    }
                },
                {
                    "id": "4742895",
                    "attributes": {"name": "Memory Care"},
                },
            ]
        }
    )

    idx = _get_people_lists_index(pco)

    assert idx["by_name"] == {
        "Active Military": "4742806",
        "Memory Care": "4742895",
    }
    assert idx["by_id"] == {
        "4742806": "Active Military",
        "4742895": "Memory Care",
    }


def test_fetch_people_names_from_list_reads_wrapped_people_payloads() -> None:
    pco = FakePCO(
        {
            "/people/v2/lists/4742806/people": [
                {
                    "data": {
                        "id": "1",
                        "attributes": {
                            "name": "LCDR Alex Turco",
                            "first_name": "Alex",
                            "last_name": "Turco",
                        },
                    }
                },
                {
                    "data": {
                        "id": "2",
                        "attributes": {
                            "name": "",
                            "first_name": "James",
                            "last_name": "Beaty",
                        },
                    }
                },
            ]
        }
    )

    names = _fetch_people_names_from_list(pco, "4742806")

    assert names == ["James Beaty", "LCDR Alex Turco"]
