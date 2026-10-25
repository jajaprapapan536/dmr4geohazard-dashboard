"""
Coordinate conversion module for Geohazard Dashboard
Supports conversion between UTM (Zone 47N, 48N) WGS84 and Latitude/Longitude (WGS84 EPSG:4326).
Supports both pyproj and pure-python standard ellipsoidal formulas as fallback.
"""
import math

try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False

# Transformers cache
_transformers_utm_to_latlon = {}
_transformers_latlon_to_utm = {}


def utm_to_latlon(easting: float, northing: float, zone: int = 47) -> tuple[float, float]:
    """
    Convert UTM (WGS84, Zone 47N or 48N) to (latitude, longitude).
    Returns (lat, lon) in decimal degrees.
    """
    if zone not in (47, 48):
        raise ValueError(f"โซน UTM ต้องเป็น 47 หรือ 48 (ประเทศไทย), แต่ได้รับ: {zone}")

    if HAS_PYPROJ:
        epsg = 32647 if zone == 47 else 32648
        if epsg not in _transformers_utm_to_latlon:
            _transformers_utm_to_latlon[epsg] = Transformer.from_crs(
                f"EPSG:{epsg}", "EPSG:4326", always_xy=True
            )
        transformer = _transformers_utm_to_latlon[epsg]
        lon, lat = transformer.transform(easting, northing)
        return round(lat, 7), round(lon, 7)

    # Pure Python WGS84 Transverse Mercator reverse projection
    a = 6378137.0
    f = 1.0 / 298.257223563
    b = a * (1.0 - f)
    e_sq = (a**2 - b**2) / (a**2)
    e_prime_sq = (a**2 - b**2) / (b**2)
    k0 = 0.9996
    cm_deg = 99.0 if zone == 47 else 105.0

    x = easting - 500000.0
    y = northing

    m = y / k0
    mu = m / (a * (1.0 - e_sq / 4.0 - 3.0 * e_sq**2 / 64.0 - 5.0 * e_sq**3 / 256.0))

    e1 = (1.0 - math.sqrt(1.0 - e_sq)) / (1.0 + math.sqrt(1.0 - e_sq))
    j1 = 3.0 * e1 / 2.0 - 27.0 * e1**3 / 32.0
    j2 = 21.0 * e1**2 / 16.0 - 55.0 * e1**4 / 32.0
    j3 = 151.0 * e1**3 / 96.0
    j4 = 1097.0 * e1**4 / 512.0

    fp = mu + j1 * math.sin(2.0 * mu) + j2 * math.sin(4.0 * mu) + j3 * math.sin(6.0 * mu) + j4 * math.sin(8.0 * mu)

    c1 = e_prime_sq * (math.cos(fp)**2)
    t1 = math.tan(fp)**2
    r1 = a * (1.0 - e_sq) / ((1.0 - e_sq * (math.sin(fp)**2))**1.5)
    n1 = a / math.sqrt(1.0 - e_sq * (math.sin(fp)**2))
    d = x / (n1 * k0)

    lat = fp - (n1 * math.tan(fp) / r1) * (
        d**2 / 2.0
        - (5.0 + 3.0 * t1 + 10.0 * c1 - 4.0 * c1**2 - 9.0 * e_prime_sq) * (d**4) / 24.0
        + (61.0 + 90.0 * t1 + 298.0 * c1 + 45.0 * t1**2 - 252.0 * e_prime_sq - 3.0 * c1**2) * (d**6) / 720.0
    )
    lon = math.radians(cm_deg) + (
        d
        - (1.0 + 2.0 * t1 + c1) * (d**3) / 6.0
        + (5.0 - 2.0 * c1 + 28.0 * t1 - 3.0 * c1**2 + 8.0 * e_prime_sq + 24.0 * t1**2) * (d**5) / 120.0
    ) / math.cos(fp)

    return round(math.degrees(lat), 7), round(math.degrees(lon), 7)


def latlon_to_utm(lat: float, lon: float) -> tuple[float, float, int]:
    """
    Convert (lat, lon) to (easting, northing, zone).
    Automatic zone detection (47 or 48 for Thailand: lon < 102 -> 47, else 48).
    """
    zone = 48 if lon >= 102.0 else 47

    if HAS_PYPROJ:
        epsg = 32647 if zone == 47 else 32648
        if epsg not in _transformers_latlon_to_utm:
            _transformers_latlon_to_utm[epsg] = Transformer.from_crs(
                "EPSG:4326", f"EPSG:{epsg}", always_xy=True
            )
        transformer = _transformers_latlon_to_utm[epsg]
        easting, northing = transformer.transform(lon, lat)
        return round(easting, 2), round(northing, 2), zone

    # Pure Python WGS84 forward projection
    a = 6378137.0
    f = 1.0 / 298.257223563
    b = a * (1.0 - f)
    e_sq = (a**2 - b**2) / (a**2)
    e_prime_sq = (a**2 - b**2) / (b**2)
    k0 = 0.9996
    cm_deg = 99.0 if zone == 47 else 105.0

    phi = math.radians(lat)
    lam = math.radians(lon)
    lam0 = math.radians(cm_deg)

    n = a / math.sqrt(1.0 - e_sq * (math.sin(phi)**2))
    t = math.tan(phi)**2
    c = e_prime_sq * (math.cos(phi)**2)
    al = (lam - lam0) * math.cos(phi)

    m = a * (
        (1.0 - e_sq / 4.0 - 3.0 * e_sq**2 / 64.0 - 5.0 * e_sq**3 / 256.0) * phi
        - (3.0 * e_sq / 8.0 + 3.0 * e_sq**2 / 32.0 + 45.0 * e_sq**3 / 1024.0) * math.sin(2.0 * phi)
        + (15.0 * e_sq**2 / 256.0 + 45.0 * e_sq**3 / 1024.0) * math.sin(4.0 * phi)
        - (35.0 * e_sq**3 / 3072.0) * math.sin(6.0 * phi)
    )

    easting = k0 * n * (
        al
        + (1.0 - t + c) * (al**3) / 6.0
        + (5.0 - 18.0 * t + t**2 + 72.0 * c - 58.0 * e_prime_sq) * (al**5) / 120.0
    ) + 500000.0

    northing = k0 * (
        m + n * math.tan(phi) * (
            (al**2) / 2.0
            + (5.0 - t + 9.0 * c + 4.0 * c**2) * (al**4) / 24.0
            + (61.0 - 58.0 * t + t**2 + 600.0 * c - 330.0 * e_prime_sq) * (al**6) / 720.0
        )
    )

    return round(easting, 2), round(northing, 2), zone
