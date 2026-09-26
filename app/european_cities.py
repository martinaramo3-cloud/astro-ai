"""Candidate cities for a relocation search.

Eighty, chosen to spread across the continent rather than to list capitals:
what matters for a relocated chart is longitude and latitude, so a search that
only knew capitals would miss whole bands of sky. Iberia, the Atlantic
seaboard, the Baltic, the Balkans and the eastern edge each need to be
represented or the answer is always "go to Lisbon".

Longer term the right shape is to search the geography first and then name the
nearest cities to the best zones. A wide list does the same job for now.
"""

EUROPEAN_CITIES = [
    # Iberia and the Atlantic
    ("Lisbon, Portugal", 38.7223, -9.1393, "Europe/Lisbon"),
    ("Porto, Portugal", 41.1579, -8.6291, "Europe/Lisbon"),
    ("Faro, Portugal", 37.0194, -7.9304, "Europe/Lisbon"),
    ("Madrid, Spain", 40.4168, -3.7038, "Europe/Madrid"),
    ("Barcelona, Spain", 41.3874, 2.1686, "Europe/Madrid"),
    ("Seville, Spain", 37.3891, -5.9845, "Europe/Madrid"),
    ("Valencia, Spain", 39.4699, -0.3763, "Europe/Madrid"),
    ("Bilbao, Spain", 43.2630, -2.9350, "Europe/Madrid"),
    ("Malaga, Spain", 36.7213, -4.4214, "Europe/Madrid"),
    ("Palma, Spain", 39.5696, 2.6502, "Europe/Madrid"),
    # France and the Low Countries
    ("Paris, France", 48.8566, 2.3522, "Europe/Paris"),
    ("Lyon, France", 45.7640, 4.8357, "Europe/Paris"),
    ("Marseille, France", 43.2965, 5.3698, "Europe/Paris"),
    ("Bordeaux, France", 44.8378, -0.5792, "Europe/Paris"),
    ("Toulouse, France", 43.6047, 1.4442, "Europe/Paris"),
    ("Nice, France", 43.7102, 7.2620, "Europe/Paris"),
    ("Nantes, France", 47.2184, -1.5536, "Europe/Paris"),
    ("Brussels, Belgium", 50.8503, 4.3517, "Europe/Brussels"),
    ("Antwerp, Belgium", 51.2194, 4.4025, "Europe/Brussels"),
    ("Amsterdam, Netherlands", 52.3676, 4.9041, "Europe/Amsterdam"),
    ("Rotterdam, Netherlands", 51.9244, 4.4777, "Europe/Amsterdam"),
    ("Luxembourg City, Luxembourg", 49.6116, 6.1319, "Europe/Luxembourg"),
    # Britain and Ireland
    ("London, United Kingdom", 51.5074, -0.1278, "Europe/London"),
    ("Manchester, United Kingdom", 53.4808, -2.2426, "Europe/London"),
    ("Edinburgh, United Kingdom", 55.9533, -3.1883, "Europe/London"),
    ("Glasgow, United Kingdom", 55.8642, -4.2518, "Europe/London"),
    ("Bristol, United Kingdom", 51.4545, -2.5879, "Europe/London"),
    ("Dublin, Ireland", 53.3498, -6.2603, "Europe/Dublin"),
    ("Cork, Ireland", 51.8985, -8.4756, "Europe/Dublin"),
    # Germany, Austria, Switzerland
    ("Berlin, Germany", 52.5200, 13.4050, "Europe/Berlin"),
    ("Munich, Germany", 48.1351, 11.5820, "Europe/Berlin"),
    ("Hamburg, Germany", 53.5511, 9.9937, "Europe/Berlin"),
    ("Frankfurt, Germany", 50.1109, 8.6821, "Europe/Berlin"),
    ("Cologne, Germany", 50.9375, 6.9603, "Europe/Berlin"),
    ("Stuttgart, Germany", 48.7758, 9.1829, "Europe/Berlin"),
    ("Leipzig, Germany", 51.3397, 12.3731, "Europe/Berlin"),
    ("Vienna, Austria", 48.2082, 16.3738, "Europe/Vienna"),
    ("Salzburg, Austria", 47.8095, 13.0550, "Europe/Vienna"),
    ("Zurich, Switzerland", 47.3769, 8.5417, "Europe/Zurich"),
    ("Geneva, Switzerland", 46.2044, 6.1432, "Europe/Zurich"),
    # Italy and the central Mediterranean
    ("Rome, Italy", 41.9028, 12.4964, "Europe/Rome"),
    ("Milan, Italy", 45.4642, 9.1900, "Europe/Rome"),
    ("Naples, Italy", 40.8518, 14.2681, "Europe/Rome"),
    ("Turin, Italy", 45.0703, 7.6869, "Europe/Rome"),
    ("Florence, Italy", 43.7696, 11.2558, "Europe/Rome"),
    ("Bologna, Italy", 44.4949, 11.3426, "Europe/Rome"),
    ("Palermo, Italy", 38.1157, 13.3615, "Europe/Rome"),
    ("Valletta, Malta", 35.8989, 14.5146, "Europe/Malta"),
    # Nordics and the Baltic
    ("Copenhagen, Denmark", 55.6761, 12.5683, "Europe/Copenhagen"),
    ("Aarhus, Denmark", 56.1629, 10.2039, "Europe/Copenhagen"),
    ("Stockholm, Sweden", 59.3293, 18.0686, "Europe/Stockholm"),
    ("Gothenburg, Sweden", 57.7089, 11.9746, "Europe/Stockholm"),
    ("Malmo, Sweden", 55.6050, 13.0038, "Europe/Stockholm"),
    ("Oslo, Norway", 59.9139, 10.7522, "Europe/Oslo"),
    ("Bergen, Norway", 60.3913, 5.3221, "Europe/Oslo"),
    ("Helsinki, Finland", 60.1699, 24.9384, "Europe/Helsinki"),
    ("Reykjavik, Iceland", 64.1466, -21.9426, "Atlantic/Reykjavik"),
    ("Tallinn, Estonia", 59.4370, 24.7536, "Europe/Tallinn"),
    ("Riga, Latvia", 56.9496, 24.1052, "Europe/Riga"),
    ("Vilnius, Lithuania", 54.6872, 25.2797, "Europe/Vilnius"),
    # Central and eastern Europe
    ("Warsaw, Poland", 52.2297, 21.0122, "Europe/Warsaw"),
    ("Krakow, Poland", 50.0647, 19.9450, "Europe/Warsaw"),
    ("Gdansk, Poland", 54.3520, 18.6466, "Europe/Warsaw"),
    ("Prague, Czechia", 50.0755, 14.4378, "Europe/Prague"),
    ("Brno, Czechia", 49.1951, 16.6068, "Europe/Prague"),
    ("Bratislava, Slovakia", 48.1486, 17.1077, "Europe/Bratislava"),
    ("Budapest, Hungary", 47.4979, 19.0402, "Europe/Budapest"),
    ("Ljubljana, Slovenia", 46.0569, 14.5058, "Europe/Ljubljana"),
    ("Zagreb, Croatia", 45.8150, 15.9819, "Europe/Zagreb"),
    ("Split, Croatia", 43.5081, 16.4402, "Europe/Zagreb"),
    # The Balkans and the south-east
    ("Belgrade, Serbia", 44.7866, 20.4489, "Europe/Belgrade"),
    ("Sarajevo, Bosnia and Herzegovina", 43.8563, 18.4131, "Europe/Sarajevo"),
    ("Skopje, North Macedonia", 41.9981, 21.4254, "Europe/Skopje"),
    ("Tirana, Albania", 41.3275, 19.8187, "Europe/Tirane"),
    ("Podgorica, Montenegro", 42.4304, 19.2594, "Europe/Podgorica"),
    ("Sofia, Bulgaria", 42.6977, 23.3219, "Europe/Sofia"),
    ("Bucharest, Romania", 44.4268, 26.1025, "Europe/Bucharest"),
    ("Athens, Greece", 37.9838, 23.7275, "Europe/Athens"),
    ("Thessaloniki, Greece", 40.6401, 22.9444, "Europe/Athens"),
    ("Istanbul, Turkey", 41.0082, 28.9784, "Europe/Istanbul"),
    ("Nicosia, Cyprus", 35.1856, 33.3823, "Asia/Nicosia"),
]


# Everywhere else. A relocated chart turns on longitude and latitude, so a
# search confined to one continent can only ever recommend somewhere in it —
# and the best place for a given return is often nowhere near home.
WORLD_CITIES = [
    # North America
    ("New York, United States", 40.7128, -74.0060, "America/New_York"),
    ("Los Angeles, United States", 34.0522, -118.2437, "America/Los_Angeles"),
    ("Chicago, United States", 41.8781, -87.6298, "America/Chicago"),
    ("Miami, United States", 25.7617, -80.1918, "America/New_York"),
    ("San Francisco, United States", 37.7749, -122.4194, "America/Los_Angeles"),
    ("Austin, United States", 30.2672, -97.7431, "America/Chicago"),
    ("Denver, United States", 39.7392, -104.9903, "America/Denver"),
    ("Seattle, United States", 47.6062, -122.3321, "America/Los_Angeles"),
    ("Boston, United States", 42.3601, -71.0589, "America/New_York"),
    ("Toronto, Canada", 43.6532, -79.3832, "America/Toronto"),
    ("Vancouver, Canada", 49.2827, -123.1207, "America/Vancouver"),
    ("Montreal, Canada", 45.5019, -73.5674, "America/Toronto"),
    ("Mexico City, Mexico", 19.4326, -99.1332, "America/Mexico_City"),
    ("Guadalajara, Mexico", 20.6597, -103.3496, "America/Mexico_City"),
    ("Havana, Cuba", 23.1136, -82.3666, "America/Havana"),
    ("Panama City, Panama", 8.9824, -79.5199, "America/Panama"),
    # South America
    ("Sao Paulo, Brazil", -23.5505, -46.6333, "America/Sao_Paulo"),
    ("Rio de Janeiro, Brazil", -22.9068, -43.1729, "America/Sao_Paulo"),
    ("Buenos Aires, Argentina", -34.6037, -58.3816, "America/Argentina/Buenos_Aires"),
    ("Santiago, Chile", -33.4489, -70.6693, "America/Santiago"),
    ("Lima, Peru", -12.0464, -77.0428, "America/Lima"),
    ("Bogota, Colombia", 4.7110, -74.0721, "America/Bogota"),
    ("Medellin, Colombia", 6.2442, -75.5812, "America/Bogota"),
    ("Montevideo, Uruguay", -34.9011, -56.1645, "America/Montevideo"),
    ("Quito, Ecuador", -0.1807, -78.4678, "America/Guayaquil"),
    # Africa
    ("Cairo, Egypt", 30.0444, 31.2357, "Africa/Cairo"),
    ("Casablanca, Morocco", 33.5731, -7.5898, "Africa/Casablanca"),
    ("Marrakesh, Morocco", 31.6295, -7.9811, "Africa/Casablanca"),
    ("Tunis, Tunisia", 36.8065, 10.1815, "Africa/Tunis"),
    ("Lagos, Nigeria", 6.5244, 3.3792, "Africa/Lagos"),
    ("Accra, Ghana", 5.6037, -0.1870, "Africa/Accra"),
    ("Nairobi, Kenya", -1.2921, 36.8219, "Africa/Nairobi"),
    ("Addis Ababa, Ethiopia", 9.0320, 38.7469, "Africa/Addis_Ababa"),
    ("Johannesburg, South Africa", -26.2041, 28.0473, "Africa/Johannesburg"),
    ("Cape Town, South Africa", -33.9249, 18.4241, "Africa/Johannesburg"),
    ("Dakar, Senegal", 14.7167, -17.4677, "Africa/Dakar"),
    # Middle East and central Asia
    ("Dubai, United Arab Emirates", 25.2048, 55.2708, "Asia/Dubai"),
    ("Abu Dhabi, United Arab Emirates", 24.4539, 54.3773, "Asia/Dubai"),
    ("Doha, Qatar", 25.2854, 51.5310, "Asia/Qatar"),
    ("Tel Aviv, Israel", 32.0853, 34.7818, "Asia/Jerusalem"),
    ("Amman, Jordan", 31.9454, 35.9284, "Asia/Amman"),
    ("Riyadh, Saudi Arabia", 24.7136, 46.6753, "Asia/Riyadh"),
    ("Tbilisi, Georgia", 41.7151, 44.8271, "Asia/Tbilisi"),
    ("Yerevan, Armenia", 40.1792, 44.4991, "Asia/Yerevan"),
    ("Almaty, Kazakhstan", 43.2220, 76.8512, "Asia/Almaty"),
    ("Tashkent, Uzbekistan", 41.2995, 69.2401, "Asia/Tashkent"),
    # South and east Asia
    ("Mumbai, India", 19.0760, 72.8777, "Asia/Kolkata"),
    ("Delhi, India", 28.6139, 77.2090, "Asia/Kolkata"),
    ("Bengaluru, India", 12.9716, 77.5946, "Asia/Kolkata"),
    ("Goa, India", 15.2993, 74.1240, "Asia/Kolkata"),
    ("Colombo, Sri Lanka", 6.9271, 79.8612, "Asia/Colombo"),
    ("Kathmandu, Nepal", 27.7172, 85.3240, "Asia/Kathmandu"),
    ("Bangkok, Thailand", 13.7563, 100.5018, "Asia/Bangkok"),
    ("Chiang Mai, Thailand", 18.7883, 98.9853, "Asia/Bangkok"),
    ("Singapore", 1.3521, 103.8198, "Asia/Singapore"),
    ("Kuala Lumpur, Malaysia", 3.1390, 101.6869, "Asia/Kuala_Lumpur"),
    ("Jakarta, Indonesia", -6.2088, 106.8456, "Asia/Jakarta"),
    ("Bali, Indonesia", -8.4095, 115.1889, "Asia/Makassar"),
    ("Ho Chi Minh City, Vietnam", 10.8231, 106.6297, "Asia/Ho_Chi_Minh"),
    ("Hanoi, Vietnam", 21.0278, 105.8342, "Asia/Ho_Chi_Minh"),
    ("Manila, Philippines", 14.5995, 120.9842, "Asia/Manila"),
    ("Hong Kong", 22.3193, 114.1694, "Asia/Hong_Kong"),
    ("Shanghai, China", 31.2304, 121.4737, "Asia/Shanghai"),
    ("Beijing, China", 39.9042, 116.4074, "Asia/Shanghai"),
    ("Taipei, Taiwan", 25.0330, 121.5654, "Asia/Taipei"),
    ("Seoul, South Korea", 37.5665, 126.9780, "Asia/Seoul"),
    ("Tokyo, Japan", 35.6762, 139.6503, "Asia/Tokyo"),
    ("Osaka, Japan", 34.6937, 135.5023, "Asia/Tokyo"),
    # Oceania
    ("Sydney, Australia", -33.8688, 151.2093, "Australia/Sydney"),
    ("Melbourne, Australia", -37.8136, 144.9631, "Australia/Melbourne"),
    ("Brisbane, Australia", -27.4698, 153.0251, "Australia/Brisbane"),
    ("Perth, Australia", -31.9505, 115.8605, "Australia/Perth"),
    ("Auckland, New Zealand", -36.8485, 174.7633, "Pacific/Auckland"),
    ("Wellington, New Zealand", -41.2866, 174.7756, "Pacific/Auckland"),
    ("Suva, Fiji", -18.1248, 178.4501, "Pacific/Fiji"),
    ("Honolulu, United States", 21.3069, -157.8583, "Pacific/Honolulu"),
]


# Which timezone prefixes belong to which region a question might name. The
# filter used to honour "europe" and silently ignore everything else — asking
# for the best US city searched all 157 worldwide and reported the winner as
# though the question had been answered.
# Europe keeps its curated list rather than a timezone prefix. Nicosia is in
# it deliberately and sits in Asia/Nicosia, so filtering Europe by prefix
# quietly dropped a city the list was written to include.
REGIONS = {
    "usa": ("America/New_York", "America/Chicago", "America/Denver",
            "America/Los_Angeles", "America/Phoenix", "America/Anchorage",
            "Pacific/Honolulu"),
    "americas": ("America/", "Pacific/Honolulu"),
    "asia": ("Asia/",),
    "africa": ("Africa/",),
    "oceania": ("Australia/", "Pacific/"),
    "middle east": ("Asia/Dubai", "Asia/Riyadh", "Asia/Qatar", "Asia/Jerusalem",
                    "Asia/Beirut", "Asia/Amman", "Asia/Baghdad", "Asia/Tehran",
                    "Asia/Kuwait", "Asia/Bahrain", "Asia/Muscat", "Asia/Istanbul"),
}


def as_places(region: str = "world") -> list[dict]:
    """Candidates for a relocation search.

    A named region narrows it; anything else searches everywhere, because the
    best place for a given chart is frequently not on the asker's continent
    and a search that cannot leave one will never say so.
    """
    everything = [
        {"label": label, "latitude": lat, "longitude": lon, "timezone": tz}
        for label, lat, lon, tz in EUROPEAN_CITIES + WORLD_CITIES
    ]
    wanted = (region or "world").lower()
    if wanted == "europe":
        return everything[:len(EUROPEAN_CITIES)]
    prefixes = REGIONS.get(wanted)
    if not prefixes:
        return everything
    return [c for c in everything if c["timezone"].startswith(prefixes)]
