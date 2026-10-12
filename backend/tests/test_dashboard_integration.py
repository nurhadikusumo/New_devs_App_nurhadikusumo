"""Run against docker-compose: RUN_DASHBOARD_INTEGRATION=1 python -m unittest discover -s tests."""

import json
import os
import unittest
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from app.api.v1.dashboard import get_dashboard_summary
from app.core.database_pool import db_pool
from app.services.reservations import calculate_total_revenue


class RevenueFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_database_failure_does_not_return_mock_revenue(self):
        with patch.object(db_pool, "session_factory", None), patch.object(
            db_pool, "initialize", new_callable=AsyncMock, side_effect=RuntimeError("database unavailable")
        ):
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                await calculate_total_revenue("prop-001", "tenant-a", 3, 2024)

    async def test_half_cent_rounds_after_aggregation(self):
        revenue = {"property_id": "prop-001", "total": "1.005", "currency": "USD", "count": 1}
        with patch("app.api.v1.dashboard.get_revenue_summary", new_callable=AsyncMock, return_value=revenue):
            result = await get_dashboard_summary("prop-001", 3, 2024, SimpleNamespace(tenant_id="tenant-a"))
        self.assertEqual("1.01", result["total_revenue"])

    async def test_mixed_currencies_are_rejected(self):
        row = SimpleNamespace(total_revenue="3.000", reservation_count=2, currency_count=2, currency="EUR")

        class FakeSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def execute(self, *args):
                return SimpleNamespace(fetchone=lambda: row)

        fake_pool = SimpleNamespace(session_factory=True, get_session=FakeSession)
        with patch("app.services.reservations.db_pool", fake_pool):
            with self.assertRaises(HTTPException) as failure:
                await calculate_total_revenue("prop-001", "tenant-a", 3, 2024)
        self.assertEqual(409, failure.exception.status_code)


@unittest.skipUnless(os.getenv("RUN_DASHBOARD_INTEGRATION") == "1", "Requires running docker-compose services")
class DashboardIntegrationTests(unittest.TestCase):
    base = os.getenv("DASHBOARD_TEST_URL", "http://localhost:8000/api/v1")

    @classmethod
    def setUpClass(cls):
        cls.sunset = cls.login("sunset@propertyflow.com", "client_a_2024")
        cls.ocean = cls.login("ocean@propertyflow.com", "client_b_2024")

    @classmethod
    def login(cls, email, password):
        request = urllib.request.Request(
            cls.base + "/auth/login",
            json.dumps({"email": email, "password": password}).encode(),
            {"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            return json.load(response)["access_token"]

    def get(self, token, path):
        request = urllib.request.Request(
            self.base + path, headers={"Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def summary(self, token, property_id, month):
        return self.get(token, f"/dashboard/summary?property_id={property_id}&month={month}&year=2024")

    def test_cache_does_not_cross_tenants(self):
        sunset_first = self.summary(self.sunset, "prop-001", 3)
        ocean = self.summary(self.ocean, "prop-001", 3)
        sunset_again = self.summary(self.sunset, "prop-001", 3)
        self.assertEqual("2250.00", sunset_first["total_revenue"])
        self.assertEqual(4, sunset_first["reservations_count"])
        self.assertEqual("0.00", ocean["total_revenue"])
        self.assertEqual(sunset_first, sunset_again)

    def test_local_march_boundary(self):
        self.assertEqual("0.00", self.summary(self.sunset, "prop-001", 2)["total_revenue"])
        self.assertEqual("2250.00", self.summary(self.sunset, "prop-001", 3)["total_revenue"])

    def test_other_tenant_property_is_hidden(self):
        ocean_properties = self.get(self.ocean, "/dashboard/properties")
        self.assertNotIn("prop-002", [item["id"] for item in ocean_properties])
        with self.assertRaises(urllib.error.HTTPError) as failure:
            self.summary(self.ocean, "prop-002", 3)
        self.assertEqual(404, failure.exception.code)


if __name__ == "__main__":
    unittest.main()
