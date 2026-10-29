import pytest

from netnama.core.finglish import transliterate
from netnama.core.names import catalog, classify, compose, inspect_word, search
from netnama.core.validation import ValidationError


@pytest.mark.parametrize(
    ("text", "latin"),
    [
        ("نگین", "negin"),
        ("فرش", "farsh"),
        ("کاشان", "kashan"),
        ("تبریز", "tabriz"),
        ("اصفهان", "esfahan"),
        ("علی", "ali"),
        ("سارا", "sara"),
        ("خانه", "khane"),
        ("نگین فرش", "neginfarsh"),
        ("Carpet", "carpet"),
    ],
)
def test_transliterate(text, latin):
    assert transliterate(text) == latin


def test_catalog_covers_published_dataset():
    data = catalog()
    assert data["count"] > 10000
    assert data["source"].endswith("persian-names")
    assert "نگین" in data["index"]


def test_search_prefers_prefix_and_reports_gender():
    result = search("نگ", limit=10)
    assert result["items"][0]["name"] == "نگین" or result["items"][0]["name"].startswith("نگ")
    assert result["items"][0]["latin"]
    assert result["count"] > 10000
    assert search("", limit=5)["items"]


def test_classify_and_inspect():
    assert classify("کاشان") == "place"
    assert classify("نگین") == "name"
    assert classify("فرش") == "keyword"
    inspected = inspect_word("  نِگین ")
    assert inspected["latin"] == "negin"
    assert inspected["role"] == "name"


def test_compose_brand_orders_and_tlds():
    result = compose(
        [
            {"fa": "نگین", "role": "name"},
            {"fa": "فرش", "role": "keyword"},
            {"fa": "کاشان", "role": "place"},
        ],
        ["ir", ".com", "ir"],
    )
    labels = [item["label"] for item in result["labels"]]
    assert labels[0] == "neginfarshkashan"
    assert "neginfarsh" in labels
    assert "negin-farsh" in labels
    assert "farshnegin" in labels
    domains = {item["domain"] for item in result["domains"]}
    assert "neginfarsh.ir" in domains
    assert "neginfarsh.com" in domains
    assert all(not item["domain"].endswith("..") for item in result["domains"])


def test_compose_keeps_edited_latin():
    result = compose([{"fa": "نگین", "latin": "NeginShop", "role": "name"}], ["com"], ["joined"])
    assert result["tokens"][0]["latin"] == "neginshop"
    assert result["domains"] == [
        {
            "domain": "neginshop.com",
            "label": "neginshop",
            "tld": "com",
            "persian": "نگین",
            "kind": "full",
        }
    ]


def test_names_api(client, login, app):
    assert app.test_client().get("/api/names?q=نگین").status_code == 401
    found = client.get("/api/names?q=نگین", headers=login)
    assert found.status_code == 200
    assert found.json["items"][0]["name"] == "نگین"
    assert found.json["items"][0]["latin"] == "negin"
    inspected = client.post("/api/names/inspect", json={"text": "کاشان"}, headers=login)
    assert inspected.json["role"] == "place"
    assert inspected.json["latin"] == "kashan"
    composed = client.post(
        "/api/names/compose",
        json={"tokens": [{"fa": "نگین", "role": "name"}, {"fa": "فرش", "role": "keyword"}], "tlds": ["ir", "com"]},
        headers=login,
    )
    assert composed.status_code == 200
    assert "neginfarsh.ir" in {item["domain"] for item in composed.json["domains"]}
    page = client.get("/tools/domain_names")
    assert page.status_code == 200
    assert b'id="name-studio"' in page.data


def test_compose_rejects_empty_and_overflow():
    with pytest.raises(ValidationError):
        compose([], ["ir"])
    with pytest.raises(ValidationError):
        compose([{"fa": "فرش"}] * 9, ["ir"])
    with pytest.raises(ValidationError):
        compose([{"fa": "فرش"}], ["."])
