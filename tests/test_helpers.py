"""Tests for CatLink helper functions."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.catlink.const import DOMAIN
from custom_components.catlink.helpers import (
    Helper,
    async_setup_domain_platform,
    as_int,
    discover_region,
    format_api_error,
    parse_phone_number,
)


class TestParsePhoneNumber:
    """Tests for parse_phone_number."""

    def test_international_format_with_plus(self) -> None:
        """Test parsing international format with plus."""
        assert parse_phone_number("+447911123456") == ("44", "7911123456")

    def test_international_format_without_plus(self) -> None:
        """Test parsing international format without plus."""
        assert parse_phone_number("447911123456") == ("44", "7911123456")

    def test_us_number(self) -> None:
        """Test parsing US number."""
        assert parse_phone_number("+12025551234") == ("1", "2025551234")

    def test_china_number(self) -> None:
        """Test parsing China number."""
        assert parse_phone_number("+8613812345678") == ("86", "13812345678")

    def test_with_spaces_and_dashes(self) -> None:
        """Test parsing number with formatting."""
        assert parse_phone_number("+44 7911-123-456") == ("44", "7911123456")

    def test_singapore_number(self) -> None:
        """Test parsing Singapore number."""
        assert parse_phone_number("+6591234567") == ("65", "91234567")


class TestFormatApiError:
    """Tests for format_api_error."""

    def test_with_msg_and_code(self) -> None:
        """Test formatting with msg and returnCode."""
        rdt = {
            "returnCode": 4007,
            "msg": "Protection is temporarily paused.",
            "success": False,
        }
        assert (
            format_api_error(rdt)
            == "Protection is temporarily paused. (returnCode: 4007)"
        )

    def test_with_msg_only(self) -> None:
        """Test formatting with msg only."""
        rdt = {"msg": "Device offline"}
        assert format_api_error(rdt) == "Device offline"

    def test_with_message_alias(self) -> None:
        """Test formatting with message key."""
        rdt = {"message": "Custom error", "returnCode": 500}
        assert format_api_error(rdt) == "Custom error (returnCode: 500)"

    def test_without_msg(self) -> None:
        """Test formatting when msg is missing."""
        rdt = {"returnCode": 4007, "data": {}}
        assert "4007" in format_api_error(rdt)


class TestCalculateUpdateInterval:
    """Tests for Helper.calculate_update_interval."""

    def test_timedelta_passthrough(self) -> None:
        """Test timedelta is returned as-is."""
        interval = timedelta(minutes=5)
        assert Helper.calculate_update_interval(interval) == interval

    def test_seconds_int(self) -> None:
        """Test seconds as int."""
        assert Helper.calculate_update_interval(60) == timedelta(seconds=60)

    def test_seconds_float(self) -> None:
        """Test seconds as float."""
        assert Helper.calculate_update_interval(90.5) == timedelta(seconds=90)

    def test_hhmmss_string(self) -> None:
        """Test HH:MM:SS format."""
        assert Helper.calculate_update_interval("01:30:00") == timedelta(
            hours=1, minutes=30
        )

    def test_invalid_string_defaults_to_one_minute(self) -> None:
        """Test invalid string returns 1 minute default."""
        assert Helper.calculate_update_interval("invalid") == timedelta(minutes=1)

    def test_none_defaults_to_one_minute(self) -> None:
        """Test None returns 1 minute default."""
        assert Helper.calculate_update_interval(None) == timedelta(minutes=1)

    def test_zero_or_negative_defaults_to_one_minute(self) -> None:
        """Test zero or negative returns 1 minute default."""
        assert Helper.calculate_update_interval(0) == timedelta(minutes=1)
        assert Helper.calculate_update_interval(-10) == timedelta(minutes=1)


PHONE_CREDENTIALS = {
    "phone": "13812345678",
    "phone_iac": "86",
    "password": "testpass",
}
EMAIL_CREDENTIALS = {"email": "user@example.com", "password": "testpass"}


class TestDiscoverRegion:
    """Tests for discover_region."""

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_discover_region_returns_region_on_login_success(self, hass) -> None:
        """Test discover_region returns region when login succeeds."""
        with patch(
            "custom_components.catlink.modules.account.Account"
        ) as mock_account_cls:
            mock_account = MagicMock()
            mock_account.async_login = AsyncMock(return_value=True)
            mock_account_cls.return_value = mock_account

            result = await discover_region(hass, PHONE_CREDENTIALS)

            assert result == "global"
            mock_account.async_login.assert_called_once()

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_discover_region_returns_none_when_all_fail(self, hass) -> None:
        """Test discover_region returns None when no region succeeds."""
        with patch(
            "custom_components.catlink.modules.account.Account"
        ) as mock_account_cls:
            mock_account = MagicMock()
            mock_account.async_login = AsyncMock(return_value=False)
            mock_account_cls.return_value = mock_account

            result = await discover_region(hass, PHONE_CREDENTIALS)

            assert result is None

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_discover_region_accepts_email_credentials(self, hass) -> None:
        """Test discover_region passes email credentials through to the account."""
        with patch(
            "custom_components.catlink.modules.account.Account"
        ) as mock_account_cls:
            mock_account = MagicMock()
            mock_account.async_login = AsyncMock(return_value=True)
            mock_account_cls.return_value = mock_account

            result = await discover_region(hass, EMAIL_CREDENTIALS)

            assert result == "global"
            config = mock_account_cls.call_args[0][1]
            assert config["email"] == "user@example.com"
            assert config["api_base"] == "https://app.catlinks.cn/api/"

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_explicit_region_tries_only_that_region(self, hass) -> None:
        """Test an explicit region does not fall back to probing every server."""
        with patch(
            "custom_components.catlink.modules.account.Account"
        ) as mock_account_cls:
            mock_account = MagicMock()
            mock_account.async_login = AsyncMock(return_value=False)
            mock_account_cls.return_value = mock_account

            result = await discover_region(hass, PHONE_CREDENTIALS, region="usa")

            assert result is None
            assert mock_account.async_login.await_count == 1
            config = mock_account_cls.call_args[0][1]
            assert config["api_base"] == "https://app-usa.catlinks.cn/api/"

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_auto_region_probes_every_server(self, hass) -> None:
        """Test auto-detect tries all four regions before giving up."""
        with patch(
            "custom_components.catlink.modules.account.Account"
        ) as mock_account_cls:
            mock_account = MagicMock()
            mock_account.async_login = AsyncMock(return_value=False)
            mock_account_cls.return_value = mock_account

            assert await discover_region(hass, PHONE_CREDENTIALS) is None
            assert mock_account.async_login.await_count == 4


class TestAsyncSetupDomainPlatform:
    """Tests for async_setup_domain_platform."""

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_async_setup_domain_platform_registers_add_entities(
        self, hass
    ) -> None:
        """Test async_setup_domain_platform registers add_entities."""
        hass.data[DOMAIN] = {
            "add_entities": {},
            "coordinators": {},
        }
        add_entities = MagicMock()

        with patch(
            "custom_components.catlink.helpers.Helper.async_setup_accounts",
            new_callable=AsyncMock,
        ) as mock_setup:
            await async_setup_domain_platform(hass, "sensor", add_entities)

            assert "discovery" in hass.data[DOMAIN]["add_entities"]
            assert (
                hass.data[DOMAIN]["add_entities"]["discovery"]["sensor"] == add_entities
            )
            mock_setup.assert_called_once_with(hass, "sensor")

    @pytest.mark.usefixtures("enable_custom_integrations")
    async def test_async_setup_domain_platform_calls_extra_setup(self, hass) -> None:
        """Test async_setup_domain_platform calls extra_setup when provided."""
        hass.data[DOMAIN] = {
            "add_entities": {},
            "coordinators": {},
        }
        extra_setup = AsyncMock()

        with patch(
            "custom_components.catlink.helpers.Helper.async_setup_accounts",
            new_callable=AsyncMock,
        ):
            await async_setup_domain_platform(
                hass, "sensor", MagicMock(), extra_setup=extra_setup
            )

            extra_setup.assert_called_once()


class TestAsInt:
    """Tests for as_int."""

    def test_plain_values(self) -> None:
        """Test ints and numeric strings coerce."""
        assert as_int(5) == 5
        assert as_int("0") == 0
        assert as_int("42") == 42

    def test_none_returns_default(self) -> None:
        """Test a JSON null becomes the default, not a crash.

        The API sends the key with a null value, so dict.get(key, 0) hands back
        None and int(None) raises.
        """
        assert as_int(None) is None
        assert as_int(None, 0) == 0

    def test_empty_and_junk_return_default(self) -> None:
        """Test unparseable values fall back instead of raising."""
        assert as_int("") is None
        assert as_int("abc", 0) == 0
        assert as_int([], 7) == 7
