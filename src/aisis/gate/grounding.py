"""Rule-based argument grounding: a tool call is only executed if its required
arguments (place / crop / date / id) are actually present in the user query."""
import re

DIST = "ঢাকা গাজীপুর নারায়ণগঞ্জ নরসিংদী মানিকগঞ্জ মুন্সিগঞ্জ কিশোরগঞ্জ টাঙ্গাইল ফরিদপুর গোপালগঞ্জ মাদারীপুর রাজবাড়ী শরীয়তপুর চট্টগ্রাম কক্সবাজার কুমিল্লা ফেনী ব্রাহ্মণবাড়িয়া রাঙ্গামাটি নোয়াখালী চাঁদপুর লক্ষ্মীপুর খাগড়াছড়ি বান্দরবান সিলেট হবিগঞ্জ মৌলভীবাজার সুনামগঞ্জ রাজশাহী নাটোর নওগাঁ চাঁপাইনবাবগঞ্জ পাবনা সিরাজগঞ্জ বগুড়া জয়পুরহাট রংপুর দিনাজপুর গাইবান্ধা কুড়িগ্রাম লালমনিরহাট নীলফামারী পঞ্চগড় ঠাকুরগাঁও খুলনা বাগেরহাট সাতক্ষীরা যশোর ঝিনাইদহ মাগুরা নড়াইল কুষ্টিয়া মেহেরপুর চুয়াডাঙ্গা বরিশাল ভোলা পটুয়াখালী পিরোজপুর ঝালকাঠি বরগুনা ময়মনসিংহ জামালপুর নেত্রকোণা শেরপুর".split()
CROPS = "ধান আলু পেঁয়াজ পাট পেঁপে টমেটো বেগুন আম পেয়ারা মরিচ চাল গম ভুট্টা সরিষা মসুর".split()
DATES = "আজ কাল আগামীকাল আগামীকাইল পরশু শনিবার রবিবার সোমবার মঙ্গলবার বুধবার বৃহস্পতিবার শুক্রবার আইজ কাইল".split()
STOP = {"কাছের", "সবচেয়ে", "আমার", "এই", "ওই", "আপনার", "মোর", "এলাকার"}


def has_place(q):
    if any(x in q for x in DIST):
        return True
    for m in re.finditer(r"(\S+)\s+উপজেলা", q):
        if m.group(1) not in STOP:
            return True
    return False


def has_crop(q):
    return any(c in q for c in CROPS)


def has_date(q):
    return any(re.search(r"(^|\s)" + x, q) for x in DATES)


def has_id(q):
    return bool(re.search(r"[০-৯]{5,}", q))


def grounded(tool, q):
    return {
        "find_nearest_clinic": has_place(q),
        "get_crop_market_price": has_place(q) and has_crop(q),
        "get_weather_forecast": has_place(q) and has_date(q),
        "check_service_status": has_id(q),
    }[tool]
