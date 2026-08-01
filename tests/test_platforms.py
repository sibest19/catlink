"""Tests for CatLink platform setup (sensor, switch, binary_sensor, select, button)."""

from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.catlink import binary_sensor, button, select, sensor, switch
from custom_components.catlink.const import (
    CONF_ACCOUNTS,
    CONF_DEVICE_IDS,
    CONF_PHONE,
    CONF_PHONE_IAC,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    SUPPORTED_DOMAINS,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_DEVICES
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_account():
    """Mock Account to avoid real API calls."""
    with patch("custom_components.catlink.Account") as mock:
        instance = mock.return_value
        instance.uid = "86-13812345678"
        instance.hass = None
        instance.async_check_auth = AsyncMock()
        instance.get_devices = AsyncMock(return_value=[])
        instance.update_interval = __import__("datetime").timedelta(minutes=1)
        instance.get_config = MagicMock(return_value=None)
        yield mock


@pytest.fixture
def mock_coordinator():
    """Mock DevicesCoordinator class."""
    with patch("custom_components.catlink.DevicesCoordinator") as mock:
        instance = mock.return_value
        instance.name = f"{DOMAIN}-86-13812345678-devices"
        instance.async_refresh = AsyncMock()
        instance.data = {}
        yield mock


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PHONE_IAC: "86",
            CONF_PHONE: "13812345678",
            "api_base": "https://app.catlinks.cn/api/",
            "password": "testpass",
        },
        options={CONF_DEVICE_IDS: [], CONF_UPDATE_INTERVAL: 60},
        unique_id="86-13812345678",
    )


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_account,
    mock_coordinator,
) -> MockConfigEntry:
    """Set up the CatLink integration for platform tests."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(CONF_ACCOUNTS, {})
    hass.data[DOMAIN].setdefault(CONF_DEVICES, {})
    hass.data[DOMAIN].setdefault("coordinators", {})
    hass.data[DOMAIN].setdefault("add_entities", {})
    hass.data[DOMAIN].setdefault("config", {CONF_DEVICES: []})
    hass.data[DOMAIN].setdefault("entry_coordinators", {})

    mock_account.return_value.hass = hass

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    return mock_config_entry


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_platforms_loaded(init_integration: MockConfigEntry) -> None:
    """Test all supported platforms are loaded."""
    assert init_integration.state is ConfigEntryState.LOADED
    assert set(SUPPORTED_DOMAINS) == {
        "sensor",
        "binary_sensor",
        "switch",
        "select",
        "button",
        "number",
    }


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_add_entities_registered(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test add_entities callbacks are registered for each platform."""
    add_entities = hass.data[DOMAIN].get("add_entities", {})
    entry_add = add_entities.get(init_integration.entry_id, {})
    for domain in SUPPORTED_DOMAINS:
        assert domain in entry_add
        assert callable(entry_add[domain])


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_sensor_platform_setup_entry(
    hass: HomeAssistant,
) -> None:
    """Test sensor platform async_setup_entry registers callback and updates entities."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("add_entities", {})
    hass.data[DOMAIN].setdefault("entry_coordinators", {})

    mock_add_entities = MagicMock()
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PHONE_IAC: "86", CONF_PHONE: "13812345678"},
        entry_id="test-sensor-entry",
    )
    mock_config_entry.add_to_hass(hass)

    await sensor.async_setup_entry(hass, mock_config_entry, mock_add_entities)

    assert mock_config_entry.entry_id in hass.data[DOMAIN]["add_entities"]
    assert "sensor" in hass.data[DOMAIN]["add_entities"][mock_config_entry.entry_id]
    assert (
        hass.data[DOMAIN]["add_entities"][mock_config_entry.entry_id]["sensor"]
        is mock_add_entities
    )


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_switch_platform_setup_entry(
    hass: HomeAssistant,
) -> None:
    """Test switch platform async_setup_entry registers callback."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("add_entities", {})
    hass.data[DOMAIN].setdefault("entry_coordinators", {})

    mock_add_entities = MagicMock()
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PHONE_IAC: "86", CONF_PHONE: "13812345678"},
        entry_id="test-switch-entry",
    )
    mock_config_entry.add_to_hass(hass)

    await switch.async_setup_entry(hass, mock_config_entry, mock_add_entities)

    assert "switch" in hass.data[DOMAIN]["add_entities"][mock_config_entry.entry_id]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_all_platforms_have_setup_entry(
    hass: HomeAssistant,
) -> None:
    """Test all supported domains have async_setup_entry."""
    for _domain, module in [
        ("sensor", sensor),
        ("switch", switch),
        ("binary_sensor", binary_sensor),
        ("select", select),
        ("button", button),
    ]:
        assert hasattr(module, "async_setup_entry")
        assert callable(module.async_setup_entry)


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_entity_names_and_states_are_translated(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test names and enum states resolve through the translation files.

    Guards the whole has_entity_name + translation_key chain: a typo in the
    key path silently falls back to the raw slug, which is easy to miss.
    """
    from homeassistant.helpers import translation

    res = await translation.async_get_translations(hass, "en", "entity", {DOMAIN})

    # Entity names: <key> -> the label shown next to the device name.
    assert res["component.catlink.entity.sensor.gender_label.name"] == "Gender"
    assert res["component.catlink.entity.sensor.wifi_rssi.name"] == "Wi-Fi signal"
    assert res["component.catlink.entity.select.litter_type.name"] == "Litter type"
    assert res["component.catlink.entity.switch.quiet_mode.name"] == "Quiet mode"

    # Enum states: the slugs the device classes emit.
    assert res["component.catlink.entity.sensor.state.state.idle"] == "Idle"
    assert (
        res["component.catlink.entity.select.litter_type.state.bentonite"]
        == "Bentonite"
    )
    assert res["component.catlink.entity.select.safe_time.state.min_5"] == "5 minutes"


def test_every_entity_key_is_translated() -> None:
    """Test every entity key and enum state has a name in every language.

    _attr_name is never set (it would short-circuit the translation lookup in
    Entity._name_internal), so a key missing from the translation files ends up
    with no name at all in the UI. This walks every device class and fails loudly
    instead.
    """
    import json
    from pathlib import Path
    from unittest.mock import MagicMock

    from custom_components.catlink.devices.registry import DEVICE_TYPES

    hass_attrs = {
        "sensor": "hass_sensor",
        "binary_sensor": "hass_binary_sensor",
        "switch": "hass_switch",
        "select": "hass_select",
        "button": "hass_button",
        "number": "hass_number",
    }

    keys: dict[str, set[str]] = {domain: set() for domain in hass_attrs}
    for dtype, cls in DEVICE_TYPES.items():
        device = cls(
            {"id": "1", "deviceType": dtype, "mac": "AA", "deviceName": "x"},
            MagicMock(),
            None,
        )
        device.detail = {}
        for domain, attr in hass_attrs.items():
            keys[domain] |= set(getattr(device, attr, None) or {})

    assert sum(len(v) for v in keys.values()) > 50, "device walk found nothing"

    base = Path(__file__).parent.parent / "custom_components/catlink/translations"
    for path in sorted(base.glob("*.json")):
        entity = json.loads(path.read_text())["entity"]
        for domain, domain_keys in keys.items():
            translated = {k for k, v in entity.get(domain, {}).items() if "name" in v}
            assert not domain_keys - translated, (
                f"{path.name}: {domain} keys without a name: "
                f"{sorted(domain_keys - translated)}"
            )
            assert not translated - domain_keys, (
                f"{path.name}: {domain} names for keys no device creates: "
                f"{sorted(translated - domain_keys)}"
            )
