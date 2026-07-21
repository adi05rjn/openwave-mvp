"""Physical constants used by OpenWave."""

import math

MU0 = 4.0e-7 * math.pi
EPS0 = 1.0 / (MU0 * 299_792_458.0**2)
C0 = 1.0 / math.sqrt(MU0 * EPS0)
