from astropy.coordinates import Angle, Latitude, Longitude


class RightAscensionConverter:
    """Accept both decimal and sexigesimal representations of RA and ensure the returned
    value is a float in decimal degrees. If the input is in sexigesimal format, assume
    it is in units of hourangle."""
    regex = r"(?:\d+(?:\.\d+)?|\d{1,2}:\d{1,2}:\d{1,2}(?:\.\d+)?)"

    def to_python(self, value) -> float:
        unit = "hourangle" if ":" in value else "deg"
        return Longitude(value, unit=unit).deg

    def to_url(self, value) -> str:
        return value.to_string(unit="deg", decimal=True)


class DeclinationConverter:
    """Accept both decimal and sexigesimal representations of Dec and ensure the returned
    value is a float in decimal degrees. The input units are always assumed to be degrees."""
    regex = r"(?:\+|-)?(?:\d{1,2}:\d{1,2}:\d{1,2}(?:\.\d+)?|\d+(?:\.\d+)?)"

    def to_python(self, value) -> float:
        return Latitude(value, unit="deg").deg

    def to_url(self, value) -> str:
        return value.to_string(unit="deg", decimal=True)


class AngleConverter:
    """Accept any valid input value for an astropy.coordinates.Angle and ensure the
    returned value is a float in decimal degrees. The unit should be included in the input
    value."""
    regex = r"\d+(\.\d+)?\s?\w+"

    def to_python(self, value) -> float:
        return Angle(value).deg

    def to_url(self, value) -> str:
        return value.to_string()
