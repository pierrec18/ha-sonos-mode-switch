from unittest.mock import patch

import pytest
from conftest import MockConfigEntry
from custom_components.sonos_mode_switch.api import ApiError, InvalidAuth, normalize_url
from custom_components.sonos_mode_switch.const import DOMAIN
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.exceptions import HomeAssistantError

DATA = {"url": "http://sonos.test:8765", "token": "test-only-not-production"}


async def setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="test-service")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_entities_unload_reload(hass, api_mock):
    entry = await setup(hass)
    states = [s for s in hass.states.async_all() if "sonos_mode_switch" in s.entity_id]
    assert len(states) == 4
    assert (
        next(s for s in states if s.entity_id.startswith("select.")).state == "cinema"
    )
    assert all(call[0] == "GET" for call in api_mock.mock_calls)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_user_flow_duplicate(hass, api_mock):
    with patch(
        "custom_components.sonos_mode_switch.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=DATA
        )
        assert result["type"] == "create_entry"
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=DATA
        )
        assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "exception,error",
    [
        (InvalidAuth("rejected"), "invalid_auth"),
        (ApiError("offline"), "cannot_connect"),
    ],
)
async def test_config_errors(hass, exception, error):
    with patch(
        "custom_components.sonos_mode_switch.config_flow.SonosApi.status",
        side_effect=exception,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=DATA
        )
    assert result["errors"] == {"base": error}


async def test_options_reload(hass, api_mock):
    entry = await setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"poll_interval": 10}
    )
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert entry.runtime_data.update_interval.total_seconds() == 10


async def test_reauth(hass, api_mock):
    entry = await setup(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"token": "replacement-test-token"}
    )
    assert result["reason"] == "reauth_successful"
    await hass.async_block_till_done()
    assert entry.data["token"] == "replacement-test-token"


async def test_acceptance_not_observation(hass, api_mock):
    c = (await setup(hass)).runtime_data
    api_mock.post(DATA["url"] + "/v1/plans", json={"fingerprint": "a" * 64})
    api_mock.post(DATA["url"] + "/v1/mode", json={"id": "op-1", "result": "accepted"})
    api_mock.get(
        DATA["url"] + "/v1/operations/op-1",
        json={"id": "op-1", "mode": "music", "result": "running"},
    )
    await c.async_set_mode("music")
    assert c.data["observed_mode"] == "cinema"
    assert c.busy
    payload = next(x for x in api_mock.mock_calls if x[1].path == "/v1/mode")[2]
    assert payload["expected_fingerprint"] == "a" * 64
    with pytest.raises(HomeAssistantError, match="in progress"):
        await c.async_set_mode("cinema")
    original = c.api.request

    async def request(method, path, data=None):
        if path == "/v1/operations/op-1":
            return {"id": "op-1", "result": "succeeded"}
        return await original(method, path, data)

    with patch.object(c.api, "request", side_effect=request):
        await c.async_refresh()
    assert c.pending_operation is None


@pytest.mark.parametrize(
    "change",
    [{"stale": True}, {"devices_reachable": False}, {"active_operation_id": "other"}],
)
async def test_preflight_blocks(hass, api_mock, status, change):
    c = (await setup(hass)).runtime_data
    with (
        patch.object(c.api, "status", return_value=status | change),
        pytest.raises(HomeAssistantError),
    ):
        await c.async_set_mode("music")
    assert all(call[0] == "GET" for call in api_mock.mock_calls)


async def test_offline_recovery_and_auth(hass, api_mock):
    c = (await setup(hass)).runtime_data
    with patch.object(c.api, "status", side_effect=ApiError("offline")):
        await c.async_refresh()
        assert not c.last_update_success
    await c.async_refresh()
    assert c.last_update_success
    with patch.object(c.api, "status", side_effect=InvalidAuth("rejected")):
        await c.async_refresh()
        assert not c.last_update_success
    await hass.async_block_till_done()
    assert any(
        f["context"]["source"] == SOURCE_REAUTH
        for f in hass.config_entries.flow.async_progress()
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://user:password@host",
        "file:///tmp/foo",
        "http://host/v1",
        "http://host?token=bad",
    ],
)
def test_reject_unsafe_url(url):
    with pytest.raises(ValueError):
        normalize_url(url)


@pytest.mark.parametrize(
    "code,error",
    [
        (401, InvalidAuth),
        (403, InvalidAuth),
        (307, ApiError),
        (308, ApiError),
        (409, ApiError),
        (503, ApiError),
    ],
)
async def test_http_errors_no_retry(hass, aioclient_mock, code, error):
    from custom_components.sonos_mode_switch.api import SonosApi
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    api = SonosApi(async_get_clientsession(hass), DATA["url"], DATA["token"])
    aioclient_mock.get(DATA["url"] + "/test", status=code)
    with pytest.raises(error):
        await api.request("GET", "/test")
    assert len(aioclient_mock.mock_calls) == 1


async def test_readonly_and_noop(hass, api_mock):
    c = (await setup(hass)).runtime_data
    with (
        patch.object(c.api, "capabilities", return_value={"writes_enabled": False}),
        pytest.raises(HomeAssistantError, match="disabled"),
    ):
        await c.async_set_mode("music")
    await c.async_set_mode("cinema")
    assert all(call[0] == "GET" for call in api_mock.mock_calls)


async def test_submit_timeout_never_retried(hass, api_mock):
    c = (await setup(hass)).runtime_data
    api_mock.post(DATA["url"] + "/v1/plans", json={"fingerprint": "a" * 64})
    api_mock.post(DATA["url"] + "/v1/mode", exc=TimeoutError())
    with pytest.raises(HomeAssistantError, match="check operation status"):
        await c.async_set_mode("music")
    assert len([x for x in api_mock.mock_calls if x[1].path == "/v1/mode"]) == 1
