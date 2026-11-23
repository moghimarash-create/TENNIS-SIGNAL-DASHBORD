"""Comprehensive ATP & WTA Tournament City, Official Title, Surface, Coordinates & Timezone Registry."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

# (City, Official_Tournament_Name, Lat, Lon, Timezone, Default_Surface)
TOURNAMENT_GEO: dict[str, tuple[str, str, float, float, str, str]] = {
    "australian open": ("Melbourne", "Australian Open", -37.8216, 144.9785, "Australia/Melbourne", "Hard"),
    "roland garros": ("Paris", "Roland Garros", 48.8470, 2.2492, "Europe/Paris", "Clay"),
    "french open": ("Paris", "Roland Garros", 48.8470, 2.2492, "Europe/Paris", "Clay"),
    "wimbledon": ("London", "Wimbledon Championships", 51.4343, -0.2145, "Europe/London", "Grass"),
    "us open": ("New York", "US Open", 40.7498, -73.8470, "America/New_York", "Hard"),
    "indian wells": ("Indian Wells", "BNP Paribas Open", 33.7240, -116.3057, "America/Los_Angeles", "Hard"),
    "indian wells masters": ("Indian Wells", "BNP Paribas Open", 33.7240, -116.3057, "America/Los_Angeles", "Hard"),
    "miami": ("Miami", "Miami Open", 25.9580, -80.2389, "America/New_York", "Hard"),
    "miami masters": ("Miami", "Miami Open", 25.9580, -80.2389, "America/New_York", "Hard"),
    "monte carlo masters": ("Monte Carlo", "Monte Carlo Masters", 43.7516, 7.4406, "Europe/Monaco", "Clay"),
    "monte-carlo": ("Monte Carlo", "Monte Carlo Masters", 43.7516, 7.4406, "Europe/Monaco", "Clay"),
    "madrid": ("Madrid", "Mutua Madrid Open", 40.3688, -3.6844, "Europe/Madrid", "Clay"),
    "madrid masters": ("Madrid", "Mutua Madrid Open", 40.3688, -3.6844, "Europe/Madrid", "Clay"),
    "rome": ("Rome", "Internazionali d Italia", 41.9284, 12.4556, "Europe/Rome", "Clay"),
    "rome masters": ("Rome", "Internazionali d Italia", 41.9284, 12.4556, "Europe/Rome", "Clay"),
    "cincinnati": ("Cincinnati", "Cincinnati Open", 39.3507, -84.2730, "America/New_York", "Hard"),
    "cincinnati masters": ("Cincinnati", "Cincinnati Open", 39.3507, -84.2730, "America/New_York", "Hard"),
    "shanghai masters": ("Shanghai", "Rolex Shanghai Masters", 31.0416, 121.3653, "Asia/Shanghai", "Hard"),
    "shanghai": ("Shanghai", "Rolex Shanghai Masters", 31.0416, 121.3653, "Asia/Shanghai", "Hard"),
    "paris masters": ("Paris", "Rolex Paris Masters", 48.8386, 2.3786, "Europe/Paris", "Hard"),
    "dubai": ("Dubai", "Dubai Tennis Championships", 25.2427, 55.3436, "Asia/Dubai", "Hard"),
    "doha": ("Doha", "Qatar ExxonMobil Open", 25.3095, 51.5150, "Asia/Qatar", "Hard"),
    "abu dhabi": ("Abu Dhabi", "Mubadala Abu Dhabi Open", 24.4161, 54.4561, "Asia/Dubai", "Hard"),
    "brisbane": ("Brisbane", "Brisbane International", -27.5262, 153.0067, "Australia/Brisbane", "Hard"),
    "adelaide": ("Adelaide", "Adelaide International", -34.9189, 138.5955, "Australia/Adelaide", "Hard"),
    "adelaide 1": ("Adelaide", "Adelaide International", -34.9189, 138.5955, "Australia/Adelaide", "Hard"),
    "adelaide 2": ("Adelaide", "Adelaide International", -34.9189, 138.5955, "Australia/Adelaide", "Hard"),
    "sydney": ("Sydney", "Sydney Tennis Classic", -33.8535, 151.0715, "Australia/Sydney", "Hard"),
    "united cup": ("Sydney", "United Cup", -33.8535, 151.0715, "Australia/Sydney", "Hard"),
    "atp cup": ("Sydney", "ATP Cup", -33.8535, 151.0715, "Australia/Sydney", "Hard"),
    "hobart": ("Hobart", "Hobart International", -42.8712, 147.3264, "Australia/Hobart", "Hard"),
    "auckland": ("Auckland", "ASB Classic", -36.8540, 174.7731, "Pacific/Auckland", "Hard"),
    "melbourne": ("Melbourne", "Melbourne Summer Set", -37.8216, 144.9785, "Australia/Melbourne", "Hard"),
    "melbourne 1": ("Melbourne", "Melbourne Summer Set", -37.8216, 144.9785, "Australia/Melbourne", "Hard"),
    "melbourne 2": ("Melbourne", "Melbourne Summer Set", -37.8216, 144.9785, "Australia/Melbourne", "Hard"),
    "gippsland trophy": ("Melbourne", "Gippsland Trophy", -37.8216, 144.9785, "Australia/Melbourne", "Hard"),
    "grampians trophy": ("Melbourne", "Grampians Trophy", -37.8216, 144.9785, "Australia/Melbourne", "Hard"),
    "great ocean road open": ("Melbourne", "Great Ocean Road Open", -37.8216, 144.9785, "Australia/Melbourne", "Hard"),
    "murray river open": ("Melbourne", "Murray River Open", -37.8216, 144.9785, "Australia/Melbourne", "Hard"),
    "phillip island trophy": ("Melbourne", "Phillip Island Trophy", -37.8216, 144.9785, "Australia/Melbourne", "Hard"),
    "yarra valley classic": ("Melbourne", "Yarra Valley Classic", -37.8216, 144.9785, "Australia/Melbourne", "Hard"),
    "montpellier": ("Montpellier", "Open Sud de France", 43.5734, 3.9522, "Europe/Paris", "Hard"),
    "marseille": ("Marseille", "Open 13 Provence", 43.2725, 5.4004, "Europe/Paris", "Hard"),
    "rotterdam": ("Rotterdam", "ABN AMRO Open", 51.8832, 4.4892, "Europe/Amsterdam", "Hard"),
    "dallas": ("Dallas", "Dallas Open", 32.8414, -96.7845, "America/Chicago", "Hard"),
    "delray beach": ("Delray Beach", "Delray Beach Open", 26.4615, -80.0728, "America/New_York", "Hard"),
    "acapulco": ("Acapulco", "Abierto Mexicano Telcel", 16.7689, -99.7844, "America/Mexico_City", "Hard"),
    "los cabos": ("Los Cabos", "Los Cabos Tennis Open", 22.8905, -109.9167, "America/Mazatlan", "Hard"),
    "monterrey": ("Monterrey", "Abierto GNP Seguros", 25.6488, -100.3267, "America/Monterrey", "Hard"),
    "guadalajara": ("Guadalajara", "Guadalajara Open", 20.6806, -103.4628, "America/Mexico_City", "Hard"),
    "guadalajara 2": ("Guadalajara", "Guadalajara Open", 20.6806, -103.4628, "America/Mexico_City", "Hard"),
    "guadalajara finals": ("Guadalajara", "WTA Finals Guadalajara", 20.6806, -103.4628, "America/Mexico_City", "Hard"),
    "merida": ("Merida", "Merida Open Akron", 21.0319, -89.6267, "America/Merida", "Hard"),
    "cancun finals": ("Cancun", "WTA Finals Cancun", 21.1619, -86.8515, "America/Cancun", "Hard"),
    "fort worth finals": ("Fort Worth", "WTA Finals Fort Worth", 32.7409, -97.3693, "America/Chicago", "Hard"),
    "riyadh finals": ("Riyadh", "WTA Finals Riyadh", 24.7136, 46.6753, "Asia/Riyadh", "Hard"),
    "shenzhen finals": ("Shenzhen", "WTA Finals Shenzhen", 22.7199, 114.2478, "Asia/Shanghai", "Hard"),
    "cordoba": ("Cordoba", "Cordoba Open", -31.3689, -64.2463, "America/Argentina/Cordoba", "Clay"),
    "buenos aires": ("Buenos Aires", "Argentina Open", -34.5612, -58.4316, "America/Argentina/Buenos_Aires", "Clay"),
    "rio de janeiro": ("Rio de Janeiro", "Rio Open", -22.9774, -43.2244, "America/Sao_Paulo", "Clay"),
    "atp rio de janeiro": ("Rio de Janeiro", "Rio Open", -22.9774, -43.2244, "America/Sao_Paulo", "Clay"),
    "santiago": ("Santiago", "Chile Open", -33.3960, -70.5008, "America/Santiago", "Clay"),
    "bogota": ("Bogota", "Copa Colsanitas", 4.7110, -74.0721, "America/Bogota", "Clay"),
    "sao paulo": ("Sao Paulo", "Brasil Open", -23.5778, -46.6558, "America/Sao_Paulo", "Clay"),
    "quito": ("Quito", "Ecuador Open", -0.1807, -78.4678, "America/Guayaquil", "Clay"),
    "houston": ("Houston", "US Men's Clay Court Championship", 29.7541, -95.4194, "America/Chicago", "Clay"),
    "charleston": ("Charleston", "Credit One Charleston Open", 32.8617, -79.9022, "America/New_York", "Clay"),
    "charleston 1": ("Charleston", "Credit One Charleston Open", 32.8617, -79.9022, "America/New_York", "Clay"),
    "charleston 2": ("Charleston", "MUSC Health Women's Open", 32.8617, -79.9022, "America/New_York", "Clay"),
    "austin": ("Austin", "ATX Open", 30.3446, -97.7988, "America/Chicago", "Hard"),
    "marrakech": ("Marrakech", "Grand Prix Hassan II", 31.6295, -7.9811, "Africa/Casablanca", "Clay"),
    "rabat": ("Rabat", "Grand Prix Lalla Meryem", 34.0209, -6.8416, "Africa/Casablanca", "Clay"),
    "monastir": ("Monastir", "Jasmin Open", 35.7643, 10.8113, "Africa/Tunis", "Hard"),
    "barcelona": ("Barcelona", "Barcelona Open Banc Sabadell", 41.3931, 2.1173, "Europe/Madrid", "Clay"),
    "munich": ("Munich", "BMW Open", 48.1558, 11.6042, "Europe/Berlin", "Clay"),
    "estoril": ("Estoril", "Millennium Estoril Open", 38.7116, -9.3976, "Europe/Lisbon", "Clay"),
    "bucharest": ("Bucharest", "Tiriac Open", 44.4268, 26.1025, "Europe/Bucharest", "Clay"),
    "banja luka": ("Banja Luka", "Srpska Open", 44.7722, 17.1910, "Europe/Sarajevo", "Clay"),
    "belgrade": ("Belgrade", "Belgrade Open", 44.8300, 20.4519, "Europe/Belgrade", "Hard"),
    "belgrade 2": ("Belgrade", "Belgrade Open", 44.8300, 20.4519, "Europe/Belgrade", "Clay"),
    "geneva": ("Geneva", "Gonet Geneva Open", 46.2008, 6.1683, "Europe/Zurich", "Clay"),
    "lyon": ("Lyon", "Open Parc Auvergne Rhone Alpes", 45.7831, 4.8528, "Europe/Paris", "Clay"),
    "strasbourg": ("Strasbourg", "Internationaux de Strasbourg", 48.5964, 7.7689, "Europe/Paris", "Clay"),
    "rouen": ("Rouen", "Open Capfinances Rouen Metropole", 49.4432, 1.0999, "Europe/Paris", "Clay"),
    "stuttgart": ("Stuttgart", "BOSS Open Stuttgart", 48.8027, 9.1700, "Europe/Berlin", "Grass"),
    "s hertogenbosch": ("Hertogenbosch", "Libema Open", 51.7166, 5.3986, "Europe/Amsterdam", "Grass"),
    "s-hertogenbosch": ("Hertogenbosch", "Libema Open", 51.7166, 5.3986, "Europe/Amsterdam", "Grass"),
    "'s-hertogenbosch": ("Hertogenbosch", "Libema Open", 51.7166, 5.3986, "Europe/Amsterdam", "Grass"),
    "halle": ("Halle", "Terra Wortmann Open", 52.0620, 8.3536, "Europe/Berlin", "Grass"),
    "queen's club": ("London", "Queens Club Championships", 51.4883, -0.2117, "Europe/London", "Grass"),
    "the hsbc championships": ("London", "Queens Club Championships", 51.4883, -0.2117, "Europe/London", "Grass"),
    "berlin": ("Berlin", "Berlin Ladies Open", 52.4900, 13.2683, "Europe/Berlin", "Grass"),
    "birmingham": ("Birmingham", "Birmingham Classic", 52.4570, -1.9165, "Europe/London", "Grass"),
    "nottingham": ("Nottingham", "Nottingham Open", 52.9447, -1.1965, "Europe/London", "Grass"),
    "eastbourne": ("Eastbourne", "Eastbourne International", 50.7634, 0.2819, "Europe/London", "Grass"),
    "bad homburg": ("Bad Homburg", "Bad Homburg Open", 50.2289, 8.6214, "Europe/Berlin", "Grass"),
    "mallorca": ("Mallorca", "Mallorca Championships", 39.5122, 2.4847, "Europe/Madrid", "Grass"),
    "newport": ("Newport", "Hall of Fame Open", 41.4820, -71.3081, "America/New_York", "Grass"),
    "hamburg": ("Hamburg", "Hamburg Open", 53.5736, 9.9889, "Europe/Berlin", "Clay"),
    "bastad": ("Bastad", "Nordea Open", 56.4334, 12.8389, "Europe/Stockholm", "Clay"),
    "gstaad": ("Gstaad", "Swiss Open Gstaad", 46.4722, 7.2869, "Europe/Zurich", "Clay"),
    "umag": ("Umag", "Croatia Open Umag", 45.4519, 13.5169, "Europe/Zagreb", "Clay"),
    "kitzbuhel": ("Kitzbuhel", "Generali Open Kitzbuhel", 47.4458, 12.3958, "Europe/Vienna", "Clay"),
    "budapest": ("Budapest", "Hungarian Grand Prix", 47.4979, 19.0402, "Europe/Budapest", "Clay"),
    "palermo": ("Palermo", "Palermo Ladies Open", 38.1583, 13.3472, "Europe/Rome", "Clay"),
    "prague": ("Prague", "Livesport Prague Open", 50.1095, 14.4148, "Europe/Prague", "Hard"),
    "iasi": ("Iasi", "UniCredit Iasi Open", 47.1585, 27.6014, "Europe/Bucharest", "Clay"),
    "warsaw": ("Warsaw", "BNP Paribas Warsaw Open", 52.2297, 21.0122, "Europe/Warsaw", "Hard"),
    "lausanne": ("Lausanne", "Ladies Open Lausanne", 46.5080, 6.6265, "Europe/Zurich", "Clay"),
    "atlanta": ("Atlanta", "Atlanta Open", 33.7915, -84.3963, "America/New_York", "Hard"),
    "washington": ("Washington", "Mubadala Citi DC Open", 38.9539, -77.0369, "America/New_York", "Hard"),
    "montreal": ("Montreal", "National Bank Open", 45.5328, -73.6272, "America/Toronto", "Hard"),
    "toronto": ("Toronto", "National Bank Open", 43.7719, -79.5119, "America/Toronto", "Hard"),
    "winston-salem": ("Winston Salem", "Winston Salem Open", 36.1328, -80.2789, "America/New_York", "Hard"),
    "cleveland": ("Cleveland", "Tennis in the Land", 41.4959, -81.7031, "America/New_York", "Hard"),
    "san diego": ("San Diego", "San Diego Open", 32.7960, -117.1630, "America/Los_Angeles", "Hard"),
    "san jose": ("San Jose", "Silicon Valley Classic", 37.3382, -121.8863, "America/Los_Angeles", "Hard"),
    "chicago 1": ("Chicago", "Chicago Fall Tennis Classic", 41.8781, -87.6298, "America/Chicago", "Hard"),
    "chicago 2": ("Chicago", "Chicago Fall Tennis Classic", 41.8781, -87.6298, "America/Chicago", "Hard"),
    "new york": ("New York", "New York Open", 40.7229, -73.5906, "America/New_York", "Hard"),
    "new haven": ("New Haven", "Connecticut Open", 41.3125, -72.9597, "America/New_York", "Hard"),
    "lexington": ("Lexington", "Top Seed Open", 38.0406, -84.5037, "America/New_York", "Hard"),
    "chengdu": ("Chengdu", "Chengdu Open", 30.5728, 104.0668, "Asia/Shanghai", "Hard"),
    "hangzhou": ("Hangzhou", "Hangzhou Open", 30.2294, 120.2333, "Asia/Shanghai", "Hard"),
    "zhuhai": ("Zhuhai", "Zhuhai Championships", 22.2710, 113.5767, "Asia/Shanghai", "Hard"),
    "beijing": ("Beijing", "China Open", 40.0094, 116.3792, "Asia/Shanghai", "Hard"),
    "tokyo": ("Tokyo", "Japan Open Tennis Championships", 35.6365, 139.7897, "Asia/Tokyo", "Hard"),
    "tokyo olympics": ("Tokyo", "Olympic Tennis Event Tokyo", 35.6365, 139.7897, "Asia/Tokyo", "Hard"),
    "paris olympics": ("Paris", "Olympic Tennis Event Paris", 48.8470, 2.2492, "Europe/Paris", "Clay"),
    "osaka": ("Osaka", "Japan Women's Open", 34.6937, 135.5023, "Asia/Tokyo", "Hard"),
    "hiroshima": ("Hiroshima", "Japan Women's Open Hiroshima", 34.3853, 132.4553, "Asia/Tokyo", "Hard"),
    "seoul": ("Seoul", "Korea Open", 37.5186, 127.1219, "Asia/Seoul", "Hard"),
    "wuhan": ("Wuhan", "Wuhan Open", 30.4789, 114.4556, "Asia/Shanghai", "Hard"),
    "ningbo": ("Ningbo", "Ningbo Open", 29.8683, 121.5440, "Asia/Shanghai", "Hard"),
    "guangzhou": ("Guangzhou", "Guangzhou Open", 23.1291, 113.2644, "Asia/Shanghai", "Hard"),
    "nanchang": ("Nanchang", "Jiangxi Open", 28.6820, 115.8579, "Asia/Shanghai", "Hard"),
    "jiujiang": ("Jiujiang", "Jiangxi Open Jiujiang", 29.7051, 116.0019, "Asia/Shanghai", "Hard"),
    "zhengzhou": ("Zhengzhou", "Zhengzhou Open", 34.7466, 113.6253, "Asia/Shanghai", "Hard"),
    "shenzhen": ("Shenzhen", "Shenzhen Open", 22.5431, 114.0579, "Asia/Shanghai", "Hard"),
    "tianjin": ("Tianjin", "Tianjin Open", 39.0842, 117.2010, "Asia/Shanghai", "Hard"),
    "hong kong": ("Hong Kong", "Hong Kong Tennis Open", 22.2825, 114.1886, "Asia/Hong_Kong", "Hard"),
    "hua hin": ("Hua Hin", "Thailand Open", 12.5684, 99.9577, "Asia/Bangkok", "Hard"),
    "hua hin 2": ("Hua Hin", "Thailand Open", 12.5684, 99.9577, "Asia/Bangkok", "Hard"),
    "singapore": ("Singapore", "Singapore Tennis Open", 1.3040, 103.8744, "Asia/Singapore", "Hard"),
    "chennai": ("Chennai", "Chennai Open", 13.0569, 80.2425, "Asia/Kolkata", "Hard"),
    "pune": ("Pune", "Maharashtra Open", 18.5759, 73.7632, "Asia/Kolkata", "Hard"),
    "almaty": ("Almaty", "Almaty Open", 43.2220, 76.8512, "Asia/Almaty", "Hard"),
    "astana": ("Astana", "Astana Open", 51.1694, 71.4491, "Asia/Almaty", "Hard"),
    "nur-sultan": ("Astana", "Astana Open", 51.1694, 71.4491, "Asia/Almaty", "Hard"),
    "tashkent": ("Tashkent", "Tashkent Open", 41.2995, 69.2401, "Asia/Tashkent", "Hard"),
    "antwerp": ("Antwerp", "European Open", 51.2303, 4.4608, "Europe/Brussels", "Hard"),
    "brussels": ("Brussels", "European Open Brussels", 50.8503, 4.3517, "Europe/Brussels", "Hard"),
    "stockholm": ("Stockholm", "Stockholm Open", 59.3501, 18.0819, "Europe/Stockholm", "Hard"),
    "vienna": ("Vienna", "Erste Bank Open", 48.2014, 16.3781, "Europe/Vienna", "Hard"),
    "basel": ("Basel", "Swiss Indoors Basel", 47.5419, 7.6172, "Europe/Zurich", "Hard"),
    "linz": ("Linz", "Upper Austria Ladies Linz", 48.2939, 14.2947, "Europe/Vienna", "Hard"),
    "ostrava": ("Ostrava", "AGEL Open Ostrava", 49.8038, 18.2488, "Europe/Prague", "Hard"),
    "cluj-napoca": ("Cluj Napoca", "Transylvania Open", 46.7667, 23.5714, "Europe/Bucharest", "Hard"),
    "cluj napoca": ("Cluj Napoca", "Transylvania Open", 46.7667, 23.5714, "Europe/Bucharest", "Hard"),
    "cluj-napoca 1": ("Cluj Napoca", "Transylvania Open", 46.7667, 23.5714, "Europe/Bucharest", "Hard"),
    "cluj-napoca 2": ("Cluj Napoca", "Transylvania Open", 46.7667, 23.5714, "Europe/Bucharest", "Hard"),
    "metz": ("Metz", "Moselle Open", 49.0914, 6.1889, "Europe/Paris", "Hard"),
    "sofia": ("Sofia", "Sofia Open", 42.6689, 23.3689, "Europe/Sofia", "Hard"),
    "athens": ("Athens", "Hellenic Championship", 38.0369, 23.7867, "Europe/Athens", "Hard"),
    "moscow": ("Moscow", "Kremlin Cup", 55.7158, 37.5537, "Europe/Moscow", "Hard"),
    "st. petersburg": ("Saint Petersburg", "St Petersburg Open", 59.9722, 30.2214, "Europe/Moscow", "Hard"),
    "st petersburg": ("Saint Petersburg", "St Petersburg Open", 59.9722, 30.2214, "Europe/Moscow", "Hard"),
    "istanbul": ("Istanbul", "Istanbul Cup", 41.0082, 28.9784, "Europe/Istanbul", "Clay"),
    "antalya": ("Antalya", "Antalya Open", 36.8969, 30.7133, "Europe/Istanbul", "Hard"),
    "luxembourg": ("Luxembourg", "Luxembourg Open", 49.6116, 6.1319, "Europe/Luxembourg", "Hard"),
    "tallinn": ("Tallinn", "Tallinn Open", 59.4370, 24.7536, "Europe/Tallinn", "Hard"),
    "portoroz": ("Portoroz", "Zavarovalnica Sava Portoroz", 45.5143, 13.5921, "Europe/Ljubljana", "Hard"),
    "parma": ("Parma", "Emilia Romagna Open", 44.8015, 10.3279, "Europe/Rome", "Clay"),
    "florence": ("Florence", "UniCredit Firenze Open", 43.7696, 11.2558, "Europe/Rome", "Hard"),
    "naples": ("Naples", "Tennis Napoli Cup", 40.8518, 14.2681, "Europe/Rome", "Hard"),
    "courmayeur": ("Courmayeur", "Courmayeur Ladies Open", 45.7969, 6.9689, "Europe/Rome", "Hard"),
    "cagliari": ("Cagliari", "Sardegna Open", 39.2238, 9.1217, "Europe/Rome", "Clay"),
    "sardinia": ("Pula", "Forte Village Sardegna Open", 38.9833, 8.9500, "Europe/Rome", "Clay"),
    "gijon": ("Gijon", "Gijon Open", 43.5322, -5.6611, "Europe/Madrid", "Hard"),
    "marbella": ("Marbella", "AnyTech365 Andalucia Open", 36.5101, -4.8824, "Europe/Madrid", "Clay"),
    "tenerife": ("Tenerife", "Tenerife Ladies Open", 28.2916, -16.6291, "Atlantic/Canary", "Hard"),
    "cologne 1": ("Cologne", "bett1HULKS Indoors", 50.9384, 6.9830, "Europe/Berlin", "Hard"),
    "cologne 2": ("Cologne", "bett1HULKS Championship", 50.9384, 6.9830, "Europe/Berlin", "Hard"),
    "nurnberg": ("Nuremberg", "Nurnberger Versicherungscup", 49.4521, 11.0767, "Europe/Berlin", "Clay"),
    "lugano": ("Lugano", "Ladies Open Lugano", 46.0037, 8.9511, "Europe/Zurich", "Clay"),
    "gdynia": ("Gdynia", "BNP Paribas Poland Open", 54.5189, 18.5305, "Europe/Warsaw", "Clay"),
    "jurmala": ("Jurmala", "Baltic Open", 56.9680, 23.7704, "Europe/Riga", "Clay"),
    "tel aviv": ("Tel Aviv", "Tel Aviv Watergen Open", 32.1066, 34.8115, "Asia/Jerusalem", "Hard"),
    "next gen finals": ("Jeddah", "Next Gen ATP Finals", 21.6225, 39.1562, "Asia/Riyadh", "Hard"),
    "nextgen finals": ("Milan", "Next Gen ATP Finals", 45.4642, 9.1900, "Europe/Rome", "Hard"),
    "quebec city": ("Quebec City", "Coupe Banque Nationale", 46.8139, -71.2080, "America/Toronto", "Hard"),
    "granby": ("Granby", "Championnats Banque Nationale de Granby", 45.4001, -72.7329, "America/Toronto", "Hard"),
    "taipei": ("Taipei", "Taiwan Open", 25.0330, 121.5654, "Asia/Taipei", "Hard"),
    "laver cup": ("London", "Laver Cup", 51.5030, 0.0032, "Europe/London", "Hard"),
}


def _norm_key(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().lower()


def resolve_tournament_geo(
    tour: str,
    year: int,
    raw_tourney_name: str,
    raw_surface: str = "",
    espn_venue: str = "",
) -> dict[str, Any]:
    """Resolve exact (city, tourney_name, lat, lon, tz, surface) for any ATP/WTA tournament."""
    k = _norm_key(raw_tourney_name)
    t_up = tour.upper()

    # Special alternating / moving venues
    if "canada masters" in k or "omnium banque nationale" in k or "national bank open" in k:
        is_toronto = (year % 2 == 0) if t_up == "ATP" else (year % 2 == 1)
        if is_toronto:
            return {"city": "Toronto", "tourney": "National Bank Open", "lat": 43.7719, "lon": -79.5119, "tz": "America/Toronto", "surface": "Hard"}
        return {"city": "Montreal", "tourney": "National Bank Open", "lat": 45.5328, "lon": -73.6272, "tz": "America/Toronto", "surface": "Hard"}

    if k in ("tour finals", "nitto atp finals", "atp finals"):
        if year <= 2020:
            return {"city": "London", "tourney": "ATP Finals", "lat": 51.5030, "lon": 0.0032, "tz": "Europe/London", "surface": "Hard"}
        return {"city": "Turin", "tourney": "Nitto ATP Finals", "lat": 45.0418, "lon": 7.6515, "tz": "Europe/Rome", "surface": "Hard"}

    if "wta finals" in k:
        if "riyadh" in k or "riyadh" in _norm_key(espn_venue) or year in (2024, 2025):
            return {"city": "Riyadh", "tourney": "WTA Finals Riyadh", "lat": 24.7136, "lon": 46.6753, "tz": "Asia/Riyadh", "surface": "Hard"}
        if "indian wells" in k or "indian wells" in _norm_key(espn_venue):
            return {"city": "Indian Wells", "tourney": "WTA Finals", "lat": 33.7240, "lon": -116.3057, "tz": "America/Los_Angeles", "surface": "Hard"}
        return {"city": "Riyadh", "tourney": "WTA Finals", "lat": 24.7136, "lon": 46.6753, "tz": "Asia/Riyadh", "surface": "Hard"}

    # Exact key match
    if k in TOURNAMENT_GEO:
        city, tname, lat, lon, tz, def_surf = TOURNAMENT_GEO[k]
        surf = raw_surface.strip().title() if raw_surface.strip() else def_surf
        if surf not in ("Hard", "Clay", "Grass"):
            surf = def_surf
        return {"city": city, "tourney": tname, "lat": lat, "lon": lon, "tz": tz, "surface": surf}

    # Substring match from ESPN full sponsor title or venue string
    combo_search = f"{k} | {_norm_key(espn_venue)}"
    for gk, (city, tname, lat, lon, tz, def_surf) in sorted(TOURNAMENT_GEO.items(), key=lambda x: -len(x[0])):
        if len(gk) >= 4 and gk in combo_search:
            surf = raw_surface.strip().title() if raw_surface.strip() else def_surf
            if surf not in ("Hard", "Clay", "Grass"):
                surf = def_surf
            return {"city": city, "tourney": tname, "lat": lat, "lon": lon, "tz": tz, "surface": surf}

    # Fallback using parsed city from ESPN venue ("City, Country")
    parts = [p.strip() for p in espn_venue.split(",") if p.strip()]
    city_fb = parts[-2] if len(parts) >= 2 else (parts[0] if parts else raw_tourney_name.strip())
    surf_fb = raw_surface.strip().title() if raw_surface.strip() in ("Hard", "Clay", "Grass") else "Hard"
    return {
        "city": city_fb,
        "tourney": raw_tourney_name.strip(),
        "lat": 48.8566,
        "lon": 2.3522,
        "tz": "UTC",
        "surface": surf_fb,
    }
