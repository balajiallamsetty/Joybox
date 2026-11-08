from ..utils import utcnow, mask_phone
from ..utils.datetime_utils import now_ist

class CatalogService:
    def __init__(self, package_repo, addon_repo, offer_repo, offer_redemption_repo=None, config=None):
        self.package_repo = package_repo
        self.addon_repo = addon_repo
        self.offer_repo = offer_repo
        self.offer_redemption_repo = offer_redemption_repo
        self.config = config

    def get_packages(self):
        items = self.package_repo.find_all_active()
        for p in items:
            p["pricePerHourRupees"] = p["pricePerHourMinor"] / 100.0
        return items

    def get_package_by_code(self, code):
        pkg = self.package_repo.find_by_code(code)
        if pkg:
            pkg["pricePerHourRupees"] = pkg["pricePerHourMinor"] / 100.0
        return pkg

    def get_addons(self):
        items = self.addon_repo.find_all_active()
        for a in items:
            a["priceRupees"] = a["priceMinor"] / 100.0
        return items

    def get_active_offers(self):
        offers = self.offer_repo.find_active()
        for o in offers:
            o["promoPricePerHourRupees"] = o["promoPricePerHourMinor"] / 100.0
            limit = o.get("monthlyLimit", 5)
            used = o.get("monthlyRedemptionCount", 0)
            o["slotsRemainingThisMonth"] = max(0, limit - used)
        return offers

    def calculate_quote(self, package_code, duration_hours, addon_codes=None, apply_promo=True, event_date=None, customer_phone=None, gst_rate_percent=None):
        pkg = self.package_repo.find_by_code(package_code)
        if not pkg:
            raise ValueError(f"Package '{package_code}' not found or inactive")

        addon_codes = addon_codes or []
        included_codes = set(pkg.get("includedAddOnCodes", []))
        duplicate_addons = set(addon_codes).intersection(included_codes)
        if duplicate_addons:
            raise ValueError(f"Selected add-on(s) {list(duplicate_addons)} are already included in the {pkg['name']} package.")

        selected_addons = self.addon_repo.find_by_codes(addon_codes)
        found_codes = {a["code"] for a in selected_addons}
        missing_codes = set(addon_codes) - found_codes
        if missing_codes:
            raise ValueError(f"Add-on(s) {list(missing_codes)} not found or inactive")

        base_minor = pkg["pricePerHourMinor"] * duration_hours
        addons_minor = sum(a["priceMinor"] for a in selected_addons)

        line_items = [
            {
                "description": f"{pkg['name']} package ({duration_hours} hr{'s' if duration_hours > 1 else ''} × ₹{pkg['pricePerHourMinor'] // 100}/hr)",
                "amountMinor": base_minor,
                "amountRupees": base_minor / 100.0
            }
        ]
        for a in selected_addons:
            line_items.append({
                "description": a["name"],
                "amountMinor": a["priceMinor"],
                "amountRupees": a["priceMinor"] / 100.0
            })

        promo_applied = False
        promo_not_applied_reason = None
        discount_minor = 0

        if apply_promo:
            offer = self.offer_repo.find_by_package(package_code)
            if offer and offer.get("isActive", True):
                # 1. Validity Window Check
                valid_from = offer.get("validFrom")
                valid_until = offer.get("validUntil")
                check_date = event_date or now_ist().strftime("%Y-%m-%d")

                if valid_from and check_date < valid_from:
                    promo_not_applied_reason = f"Promotional offer starts on {valid_from}."
                elif valid_until and check_date > valid_until:
                    promo_not_applied_reason = f"Promotional offer ended on {valid_until}."
                else:
                    # 2. Per-Customer Limit Check
                    max_per_customer = offer.get("maxPerCustomer", 1)
                    norm_phone = "".join([c for c in str(customer_phone or "") if c.isdigit()])[-10:]
                    user_redemptions = 0
                    if norm_phone and getattr(self, "offer_redemption_repo", None):
                        user_redemptions = self.offer_redemption_repo.count_by_phone_and_offer(norm_phone, offer["_id"])

                    if norm_phone and user_redemptions >= max_per_customer:
                        promo_not_applied_reason = f"Promotional quota limit reached ({max_per_customer} per customer)."
                    else:
                        # 3. Monthly Quota Check
                        limit = offer.get("monthlyLimit", 5)
                        used = offer.get("monthlyRedemptionCount", 0)
                        if used < limit:
                            # 4. Percent vs Flat vs Hourly calculation with paise precision
                            if offer.get("discountPercent"):
                                pct = float(offer["discountPercent"])
                                discount_minor = round(base_minor * (pct / 100.0))
                            elif offer.get("discountFlatMinor"):
                                discount_minor = min(base_minor, int(offer["discountFlatMinor"]))
                            else:
                                promo_price_minor = offer.get("promoPricePerHourMinor", pkg["pricePerHourMinor"])
                                discount_per_hour = pkg["pricePerHourMinor"] - promo_price_minor
                                discount_minor = max(0, discount_per_hour * duration_hours)

                            if discount_minor > 0:
                                promo_applied = True
                                line_items.append({
                                    "description": f"Promotional Offer ({offer['name']})",
                                    "amountMinor": -discount_minor,
                                    "amountRupees": -(discount_minor / 100.0)
                                })
                        else:
                            promo_not_applied_reason = f"Monthly promotional quota ({limit} bookings) already claimed."
            else:
                promo_not_applied_reason = f"No active promotion applicable for {pkg['name']} package."

        taxable_minor = max(0, base_minor + addons_minor - discount_minor)
        default_gst = getattr(self.config, "GST_RATE_PERCENT", 0.0) if self.config else 0.0
        tax_rate = float(gst_rate_percent if gst_rate_percent is not None else default_gst)
        if tax_rate > 0:
            tax_minor = round(taxable_minor * (tax_rate / 100.0))
            line_items.append({
                "description": f"GST ({tax_rate:g}%)",
                "amountMinor": tax_minor,
                "amountRupees": tax_minor / 100.0
            })
        else:
            tax_minor = 0

        total_minor = taxable_minor + tax_minor

        return {
            "packageCode": pkg["code"],
            "packageName": pkg["name"],
            "durationHours": duration_hours,
            "currency": "INR",
            "lineItems": line_items,
            "baseAmountMinor": base_minor,
            "addOnsAmountMinor": addons_minor,
            "promoApplied": promo_applied,
            "promoNotAppliedReason": promo_not_applied_reason,
            "discountAmountMinor": discount_minor,
            "taxAmountMinor": tax_minor,
            "taxRatePercent": tax_rate,
            "totalAmountMinor": total_minor,
            "totalRupees": total_minor / 100.0,
            "note": "Indicative quote. Final slot lock and pricing confirmed during reservation."
        }


class InquiryService:
    def __init__(self, inquiry_repo):
        self.inquiry_repo = inquiry_repo

    def submit_inquiry(self, payload):
        now = utcnow()
        doc = dict(payload)
        doc.update({
            "source": "website",
            "status": "new",
            "isDeleted": False,
            "schemaVersion": 1,
            "createdAt": now,
            "updatedAt": now
        })
        inserted_id = self.inquiry_repo.insert(doc)
        masked = mask_phone(doc.get("phone", ""))
        return {
            "id": str(inserted_id) if inserted_id else None,
            "status": "received",
            "message": f"Thank you, {doc.get('name')}. Kiran Kumar will reach out to you on {masked} shortly."
        }

