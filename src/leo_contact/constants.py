"""Physical and geodetic constants.

All values are given in SI-derived units consistent across the package:
distances in kilometres, times in seconds, angles in radians unless a
function signature explicitly says otherwise.
"""

# --- Gravitational -----------------------------------------------------------
MU_EARTH = 398_600.4418
"""Earth's standard gravitational parameter [km^3/s^2]."""

J2 = 1.082_626_68e-3
"""Second zonal harmonic of Earth's gravity field [dimensionless]."""

# --- Geodetic (WGS84) --------------------------------------------------------
RE_EQUATORIAL = 6_378.137
"""WGS84 semi-major axis (equatorial radius) [km]."""

FLATTENING = 1 / 298.257_223_563
"""WGS84 flattening [dimensionless]."""

ECCENTRICITY_SQ = FLATTENING * (2 - FLATTENING)
"""First eccentricity squared of the WGS84 ellipsoid [dimensionless]."""

# --- Rotation ----------------------------------------------------------------
OMEGA_EARTH = 7.292_115_0e-5
"""Earth's sidereal rotation rate [rad/s]."""

SOLAR_YEAR_DAYS = 365.2422
"""Mean tropical year [days]. Used to derive the sun-synchronous condition."""

SECONDS_PER_DAY = 86_400.0

# --- LoRa --------------------------------------------------------------------
LORA_BANDWIDTH_HZ = 125_000
"""Default LoRa channel bandwidth [Hz]."""

DWELL_TIME_LIMIT_S = 0.400
"""Maximum per-channel dwell time under FCC-style regimes such as the one
applicable in the 915-928 MHz band in Chile [s]."""
