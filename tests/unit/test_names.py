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
    assert result["items"][0]["name"].startswith("نگ")
    assert result["items"][0]["latin"]
    assert result["count"] > 10000
    assert result["total"] >= len(result["items"])


def test_name_catalog_is_paged():
    first = search("", limit=2, page=1)
    second = search("", limit=2, page=2)
    assert first["total"] == first["count"]
    assert first["pages"] > 100
    assert len(first["items"]) == 2
    assert first["items"][0]["name"] != second["items"][0]["name"]
    assert search("نگین", limit=10)["items"][0]["name"] == "نگین"
    assert search("", limit=5, page=50000)["page"] == search("", limit=5)["pages"]
    with pytest.raises(ValidationError):
        search("", page=0)


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
        json={
            "tokens": [{"fa": "نگین", "role": "name"}, {"fa": "فرش", "role": "keyword"}],
            "tlds": ["ir", "com"],
        },
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


@pytest.mark.parametrize("latin", ["hello world", "brand.com", "-brand", "brand-", "a" * 64, "فروشگاه"])
def test_compose_does_not_silently_change_explicit_spelling(latin):
    with pytest.raises(ValidationError, match="studio_latin_invalid"):
        compose([{"fa": "برند", "latin": latin}], ["com"])


def test_compose_offers_business_word_pairs_without_personal_names():
    result = compose(
        [{"fa": word, "latin": word, "role": "keyword"} for word in ["green", "shop", "home"]],
        ["com"],
        ["joined"],
    )
    labels = {item["label"] for item in result["labels"]}
    assert {"greenshop", "shopgreen", "greenhome", "homegreen"} <= labels


@pytest.mark.parametrize("fa", [None, 42, [], "ا" * 41])
def test_compose_rejects_malformed_words(fa):
    with pytest.raises(ValidationError):
        compose([{"fa": fa}], ["com"])


@pytest.mark.parametrize("path", ["inspect", "compose"])
@pytest.mark.parametrize("body", [["unexpected"], "unexpected", 42])
def test_names_endpoints_reject_non_object_payload(client, login, path, body):
    response = client.post(f"/api/names/{path}", json=body, headers=login)
    assert response.status_code == 422


@pytest.mark.parametrize("suffix", ["notarealtld", "example.com", "com.invalidtld"])
def test_names_api_rejects_unknown_or_non_public_suffix(client, login, suffix):
    response = client.post(
        "/api/names/compose",
        json={"tokens": [{"fa": "نگین"}], "tlds": [suffix]},
        headers=login,
    )
    assert response.status_code == 422


def test_names_api_accepts_multi_part_public_suffix(client, login):
    response = client.post(
        "/api/names/compose",
        json={"tokens": [{"fa": "نگین"}], "tlds": ["co.ir"]},
        headers=login,
    )
    assert response.status_code == 200
    assert response.json["domains"][0]["domain"] == "negin.co.ir"


def test_names_can_check_domains_using_authoritative_job_results(client, login, app, monkeypatch):
    from tests.integration.test_auth_jobs import wait

    async def fake_execute(tool, item, *args, **kwargs):
        return {**item, "status": "likely_available", "reason_code": "rdap_not_found"}

    monkeypatch.setattr(app.extensions["scheduler"], "execute", fake_execute)
    composed = client.post(
        "/api/names/compose", json={"tokens": [{"fa": "نگین"}], "tlds": ["com"]}, headers=login
    ).json
    response = client.post(
        "/api/jobs",
        json={"tool": "domain_batch", "text": composed["domains"][0]["domain"]},
        headers=login,
    )
    assert response.status_code == 202
    result = wait(client, response.json["job_id"])
    assert result["results"][0]["ascii"] == "negin.com"
    assert result["results"][0]["status"] == "likely_available"
