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


def as_places() -> list[dict]:
    return [
        {"label": label, "latitude": lat, "longitude": lon, "timezone": tz}
        for label, lat, lon, tz in EUROPEAN_CITIES
    ]
