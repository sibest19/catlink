"""Tests for CatLink config flow."""

from unittest.mock import AsyncMock, patch

from custom_components.catlink.config_flow import _device_label
from custom_components.catlink.const import (
    CONF_DEVICE_IDS,
    CONF_PHONE,
    CONF_PHONE_IAC,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    ERROR_INVALID_AUTH,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import data_entry_flow
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.core import HomeAssistant


class TestDeviceLabel:
    """Tests for _device_label helper."""

    def test_device_label_with_name_and_model(self) -> None:
        """Test label when device has name and model."""
        dat = {
            "deviceName": "Living Room",
            "model": "LB599",
            "deviceType": "LITTER_BOX_599",
        }
        assert _device_label(dat, True) == "Living Room (LB599) - Supported"
        assert _device_label(dat, False) == "Living Room (LB599) - Limited support"

    def test_device_label_name_equals_model(self) -> None:
        """Test label when name equals model uses deviceType."""
        dat = {
            "deviceName": "LB599",
            "model": "LB599",
            "deviceType": "LITTER_BOX_599",
        }
        assert _device_label(dat, True) == "LB599 (LITTER_BOX_599) - Supported"

    def test_device_label_fallback_to_model(self) -> None:
        """Test label falls back to model when deviceName missing."""
        dat = {"model": "LB599", "deviceType": "LITTER_BOX_599"}
        assert _device_label(dat, True) == "LB599 (LITTER_BOX_599) - Supported"

    def test_device_label_fallback_to_unknown(self) -> None:
        """Test label falls back to Unknown when name and model missing."""
        dat = {"deviceType": "UNKNOWN"}
        assert _device_label(dat, True) == "Unknown (UNKNOWN) - Supported"


@pytest.fixture(autouse=True)
def mock_discover_region():
    """Mock discover_region to avoid real API calls."""
    with patch(
        "custom_components.catlink.config_flow.discover_region",
        new_callable=AsyncMock,
        return_value="global",
    ) as mock:
        yield mock


@pytest.fixture
def mock_account():
    """Mock Account class."""
    with patch("custom_components.catlink.config_flow.Account") as mock:
        instance = mock.return_value
        instance.uid = "86-13812345678"
        instance.async_check_auth = AsyncMock()
        instance.get_devices = AsyncMock(return_value=[])
        yield mock


async def _start(hass: HomeAssistant, method: str) -> dict:
    """Open the flow and pick a sign-in method from the menu."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": method}
    )


PHONE_INPUT = {"phone": "+8613812345678", "password": "testpass"}
EMAIL_INPUT = {"email": "user@example.com", "password": "testpass"}

ONE_DEVICE = [
    {
        "id": "dev1",
        "deviceName": "Litter Box",
        "model": "LB599",
        "deviceType": "LITTER_BOX_599",
    }
]


async def test_user_step_shows_method_menu(
    hass: HomeAssistant, enable_custom_integrations
) -> None:
    """Test the flow opens with a choice of sign-in method."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "user"
    assert result["menu_options"] == ["email", "phone"]


@pytest.mark.parametrize(
    ("method", "expected_fields"),
    [
        ("phone", ("phone", "password", "region")),
        ("email", ("email", "password", "region")),
    ],
)
async def test_method_step_form_fields(
    hass: HomeAssistant, enable_custom_integrations, method, expected_fields
) -> None:
    """Test each sign-in form exposes its identity, password and region fields."""
    result = await _start(hass, method)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == method
    for field in expected_fields:
        assert field in result["data_schema"].schema


async def test_phone_step_success_no_devices(
    hass: HomeAssistant, enable_custom_integrations, mock_account
) -> None:
    """Test successful phone flow with no devices."""
    result = await _start(hass, "phone")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], PHONE_INPUT
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "+8613812345678"
    assert result["data"]["phone_iac"] == "86"
    assert result["data"]["phone"] == "13812345678"
    assert result["data"]["api_base"] == "https://app.catlinks.cn/api/"
    assert result["data"]["region"] == "global"


async def test_email_step_success_no_devices(
    hass: HomeAssistant, enable_custom_integrations, mock_account
) -> None:
    """Test successful email flow stores the address and no phone fields."""
    mock_account.return_value.uid = "email-user@example.com"

    result = await _start(hass, "email")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], EMAIL_INPUT
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "user@example.com"
    assert result["data"]["email"] == "user@example.com"
    assert "phone" not in result["data"]
    assert result["data"]["api_base"] == "https://app.catlinks.cn/api/"


async def test_email_step_trims_whitespace(
    hass: HomeAssistant, enable_custom_integrations, mock_account
) -> None:
    """Test a pasted address with stray spaces is cleaned up."""
    mock_account.return_value.uid = "email-user@example.com"

    result = await _start(hass, "email")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"email": "  user@example.com  ", "password": "testpass"}
    )

    assert result["data"]["email"] == "user@example.com"


@pytest.mark.parametrize(
    ("method", "user_input"), [("phone", PHONE_INPUT), ("email", EMAIL_INPUT)]
)
async def test_step_success_with_devices(
    hass: HomeAssistant, enable_custom_integrations, mock_account, method, user_input
) -> None:
    """Test both methods proceed to discovery when devices exist."""
    mock_account.return_value.get_devices = AsyncMock(return_value=ONE_DEVICE)

    result = await _start(hass, method)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "discovery"


@pytest.mark.parametrize(
    ("method", "user_input"), [("phone", PHONE_INPUT), ("email", EMAIL_INPUT)]
)
async def test_step_invalid_auth_redisplays_own_form(
    hass: HomeAssistant, enable_custom_integrations, method, user_input
) -> None:
    """Test a rejected login re-shows the same step, not the menu."""
    with patch(
        "custom_components.catlink.config_flow.discover_region",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await _start(hass, method)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == method
    assert result["errors"]["base"] == ERROR_INVALID_AUTH


async def test_region_auto_is_passed_as_none(
    hass: HomeAssistant, enable_custom_integrations, mock_account, mock_discover_region
) -> None:
    """Test the auto option asks discover_region to probe every server."""
    result = await _start(hass, "phone")
    await hass.config_entries.flow.async_configure(result["flow_id"], PHONE_INPUT)

    assert mock_discover_region.call_args[0][2] is None


async def test_explicit_region_is_forwarded(
    hass: HomeAssistant, enable_custom_integrations, mock_account, mock_discover_region
) -> None:
    """Test a chosen region is forwarded instead of probing."""
    mock_discover_region.return_value = "usa"

    result = await _start(hass, "phone")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**PHONE_INPUT, "region": "usa"}
    )

    assert mock_discover_region.call_args[0][2] == "usa"
    assert result["data"]["region"] == "usa"
    assert result["data"]["api_base"] == "https://app-usa.catlinks.cn/api/"


async def test_discovery_step_form(
    hass: HomeAssistant, enable_custom_integrations, mock_account
) -> None:
    """Test discovery step shows device selection and update interval."""
    mock_account.return_value.get_devices = AsyncMock(
        return_value=[
            *ONE_DEVICE,
            {
                "id": "dev2",
                "deviceName": "Feeder",
                "model": "FD001",
                "deviceType": "FEEDER",
            },
        ]
    )

    result = await _start(hass, "phone")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], PHONE_INPUT
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "discovery"
    assert CONF_DEVICE_IDS in result["data_schema"].schema
    assert CONF_UPDATE_INTERVAL in result["data_schema"].schema


async def test_discovery_step_create_entry(
    hass: HomeAssistant, enable_custom_integrations, mock_account
) -> None:
    """Test discovery step creates entry with selected devices and interval."""
    mock_account.return_value.get_devices = AsyncMock(return_value=ONE_DEVICE)

    result = await _start(hass, "phone")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], PHONE_INPUT
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_DEVICE_IDS: ["dev1"], CONF_UPDATE_INTERVAL: 120},
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "+8613812345678"
    assert result["options"][CONF_DEVICE_IDS] == ["dev1"]
    assert result["options"][CONF_UPDATE_INTERVAL] == 120


async def test_duplicate_account_with_no_devices_aborts(
    hass: HomeAssistant, enable_custom_integrations, mock_account
) -> None:
    """Test an already-configured account cannot be added again."""
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PHONE_IAC: "86", CONF_PHONE: "13812345678"},
        unique_id="86-13812345678",
    ).add_to_hass(hass)

    result = await _start(hass, "phone")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], PHONE_INPUT
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_phone_entry_skips_menu(
    hass: HomeAssistant, enable_custom_integrations, mock_account
) -> None:
    """Test reauth of a phone account goes straight to the phone form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PHONE_IAC: "86",
            CONF_PHONE: "13812345678",
            "api_base": "https://app.catlinks.cn/api/",
            "password": "oldpass",
        },
        unique_id="86-13812345678",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "phone"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"phone": "+8613812345678", "password": "newpass"},
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PHONE] == "13812345678"
    assert entry.data["password"] == "newpass"


async def test_reauth_email_entry_skips_menu(
    hass: HomeAssistant, enable_custom_integrations, mock_account
) -> None:
    """Test reauth of an email account goes straight to the email form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": "user@example.com",
            "api_base": "https://app.catlinks.cn/api/",
            "password": "oldpass",
        },
        unique_id="email-user@example.com",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "email"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"email": "user@example.com", "password": "newpass"},
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["email"] == "user@example.com"
    assert entry.data["password"] == "newpass"


async def test_reauth_flow_invalid_auth(
    hass: HomeAssistant, enable_custom_integrations
) -> None:
    """Test reauth flow shows error when auth fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PHONE_IAC: "86",
            CONF_PHONE: "13812345678",
            "api_base": "https://app.catlinks.cn/api/",
            "password": "oldpass",
        },
        unique_id="86-13812345678",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.catlink.config_flow.discover_region",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
            data=entry.data,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"phone": "+8613812345678", "password": "wrongpass"},
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == ERROR_INVALID_AUTH


async def test_options_flow(
    hass: HomeAssistant, enable_custom_integrations, mock_account
) -> None:
    """Test options flow updates device selection and refresh interval."""
    mock_account.return_value.get_devices = AsyncMock(
        return_value=[
            *ONE_DEVICE,
            {
                "id": "dev2",
                "deviceName": "Feeder",
                "model": "FD001",
                "deviceType": "FEEDER",
            },
        ]
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PHONE_IAC: "86",
            CONF_PHONE: "13812345678",
            "api_base": "https://app.catlinks.cn/api/",
            "password": "testpass",
        },
        options={CONF_DEVICE_IDS: ["dev1"], CONF_UPDATE_INTERVAL: 60},
        unique_id="86-13812345678",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_DEVICE_IDS: ["dev1", "dev2"], CONF_UPDATE_INTERVAL: 300},
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE_IDS] == ["dev1", "dev2"]
    assert result["data"][CONF_UPDATE_INTERVAL] == 300
