import pytest
from app import create_app
from app.repositories import PackageRepository, AddOnRepository, OfferRepository, InquiryRepository
from app.services import CatalogService, InquiryService

class MockCollection:
    def __init__(self, data=None):
        self.data = list(data or [])
        self.inserted = []

    def find(self, query=None):
        query = query or {}
        class MockCursor:
            def __init__(self, items):
                self.items = items
            def sort(self, field, direction):
                return self
            def __iter__(self):
                return iter(self.items)
            def __list__(self):
                return list(self.items)
        
        filtered = []
        for doc in self.data:
            match = True
            for k, v in query.items():
                if isinstance(v, dict) and "$in" in v:
                    if doc.get(k) not in v["$in"]:
                        match = False
                        break
                elif doc.get(k) != v:
                    match = False
                    break
            if match:
                filtered.append(doc)
        return MockCursor(filtered)

    def find_one(self, query=None):
        for doc in self.data:
            match = True
            for k, v in (query or {}).items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                return dict(doc)
        return None

    def insert_one(self, doc):
        self.inserted.append(doc)
        class MockResult:
            inserted_id = "607f1f77bcf86cd799439099"
        return MockResult()

class MockDB:
    def __init__(self):
        self.packages = MockCollection([
            {
                "code": "basic",
                "name": "Basic",
                "pricePerHourMinor": 99900,
                "currency": "INR",
                "features": ["AC room", "Theme decor", "Music"],
                "includedAddOnCodes": [],
                "isActive": True,
                "displayOrder": 1
            },
            {
                "code": "gold",
                "name": "Gold",
                "pricePerHourMinor": 150000,
                "currency": "INR",
                "features": ["Cake 0.5kg", "Name display"],
                "includedAddOnCodes": [],
                "isActive": True,
                "displayOrder": 2
            },
            {
                "code": "diamond",
                "name": "Diamond",
                "pricePerHourMinor": 250000,
                "currency": "INR",
                "features": ["All Gold", "Bubble entry", "Fog entry", "Cold fire"],
                "includedAddOnCodes": ["bubble_entry", "fog_entry", "cold_fire_one_shot"],
                "isActive": True,
                "displayOrder": 3
            }
        ])
        self.addOns = MockCollection([
            {"code": "bubble_entry", "name": "Bubble Entry", "priceMinor": 30000, "isActive": True, "displayOrder": 1},
            {"code": "fog_entry", "name": "Fog Entry", "priceMinor": 50000, "isActive": True, "displayOrder": 2},
            {"code": "cold_fire_one_shot", "name": "Cold Fire", "priceMinor": 30000, "isActive": True, "displayOrder": 3}
        ])
        self.offers = MockCollection([
            {
                "name": "Introductory Offer",
                "eligiblePackageCode": "basic",
                "promoPricePerHourMinor": 50000,
                "monthlyLimit": 5,
                "monthlyRedemptionCount": 2,
                "isActive": True
            }
        ])
        self.inquiries = MockCollection([])
        self.galleryAssets = MockCollection([
            {"code": "neon_bday", "title": "Neon Birthday", "category": "birthday", "isActive": True, "displayOrder": 1, "url": "https://example.com/1.jpg"},
            {"code": "dj_night", "title": "DJ Adda", "category": "adda", "isActive": True, "displayOrder": 2, "url": "https://example.com/2.jpg", "storageKey": "secret-storage-key"}
        ])
        self.faqs = MockCollection([
            {"code": "advance_booking", "question": "How far in advance?", "category": "booking", "isActive": True, "displayOrder": 1, "answer": "2-3 days"}
        ])

    def command(self, cmd):
        if cmd == "ping":
            return {"ok": 1}
        return {}

@pytest.fixture
def test_client(monkeypatch):
    app = create_app({"TESTING": True, "MONGODB_URI": "", "FRONTEND_ORIGIN": "http://localhost:5173"})
    mock_db = MockDB()
    app.extensions["mongo_db"] = mock_db
    with app.test_client() as client:
        yield client

def test_health_check(test_client):
    res = test_client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"
    assert data["data"]["database"] == "connected"

def test_get_packages(test_client):
    res = test_client.get("/api/packages")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["data"]["items"]) == 3
    assert data["data"]["items"][0]["code"] == "basic"
    assert data["data"]["items"][0]["pricePerHourMinor"] == 99900
    assert data["data"]["items"][0]["pricePerHourRupees"] == 999.0

def test_get_package_by_slug(test_client):
    res = test_client.get("/api/packages/gold")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["code"] == "gold"
    assert data["data"]["pricePerHourMinor"] == 150000

def test_get_package_by_slug_not_found(test_client):
    res = test_client.get("/api/packages/platinum")
    assert res.status_code == 404
    data = res.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"

def test_get_addons(test_client):
    res = test_client.get("/api/add-ons")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["data"]["items"]) == 3
    assert data["data"]["items"][1]["code"] == "fog_entry"
    assert data["data"]["items"][1]["priceMinor"] == 50000

def test_get_active_offers(test_client):
    res = test_client.get("/api/offers/active")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["data"]["offers"]) == 1
    offer = data["data"]["offers"][0]
    assert offer["eligiblePackageCode"] == "basic"
    assert offer["promoPricePerHourMinor"] == 50000
    assert offer["slotsRemainingThisMonth"] == 3

def test_booking_quote_with_promo(test_client):
    payload = {
        "packageCode": "basic",
        "durationHours": 2,
        "addOnCodes": ["bubble_entry"],
        "applyPromo": True
    }
    res = test_client.post("/api/bookings/quote", json=payload)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["packageCode"] == "basic"
    assert data["promoApplied"] is True
    # (99900 * 2) + 30000 - ((99900 - 50000) * 2) = 100000 + 30000 = 130000 paise (₹1,300)
    assert data["baseAmountMinor"] == 199800
    assert data["discountAmountMinor"] == 99800
    assert data["totalAmountMinor"] == 130000
    assert data["totalRupees"] == 1300.0

def test_booking_quote_duplicate_addon_rejected(test_client):
    payload = {
        "packageCode": "diamond",
        "durationHours": 2,
        "addOnCodes": ["fog_entry"]
    }
    res = test_client.post("/api/bookings/quote", json=payload)
    assert res.status_code == 422
    data = res.get_json()
    assert data["success"] is False
    assert "already included" in data["error"]["message"]

def test_create_inquiry(test_client):
    payload = {
        "name": "Ravi Kumar",
        "phone": "+91 98765 43210",
        "preferredDate": "2026-11-15",
        "packageCode": "gold",
        "durationHours": 3,
        "message": "Looking forward to birthday celebration"
    }
    res = test_client.post("/api/inquiries", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["status"] == "received"
    assert "Kiran Kumar" in data["data"]["message"]
    assert "****3210" in data["data"]["message"]

def test_inquiry_validation_error(test_client):
    payload = {
        "name": "A", # Too short
        "phone": "123"
    }
    res = test_client.post("/api/inquiries", json=payload)
    assert res.status_code == 422
    data = res.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"

def test_get_gallery_strips_storage_key(test_client):
    res = test_client.get("/api/gallery")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    items = data["data"]["items"]
    assert len(items) == 2
    for item in items:
        assert "storageKey" not in item

def test_get_gallery_category_filter(test_client):
    res = test_client.get("/api/gallery?category=birthday")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    items = data["data"]["items"]
    assert len(items) == 1
    assert items[0]["category"] == "birthday"

def test_get_faqs(test_client):
    res = test_client.get("/api/faqs")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["data"]["items"]) == 1
    assert data["data"]["items"][0]["question"] == "How far in advance?"
