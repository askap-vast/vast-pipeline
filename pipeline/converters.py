from astropy.coordinates import Angle, Latitude, Longitude


class RightAscensionConverter:
    regex = r"(?:\d+(?:\.\d+)?|\d{1,2}:\d{1,2}:\d{1,2}(?:\.\d+)?)"

    def to_python(self, value) -> float:
        unit = "hourangle" if ":" in value else "deg"
        return Longitude(value, unit=unit).deg

    def to_url(self, value) -> str:
        return value.to_string(unit="deg", decimal=True)


class DeclinationConverter:
    regex = r"(?:\+|-)?(?:\d{1,2}:\d{1,2}:\d{1,2}(?:\.\d+)?|\d+(?:\.\d+)?)"

    def to_python(self, value) -> float:
        return Latitude(value, unit="deg").deg

    def to_url(self, value) -> str:
        return value.to_string(unit="deg", decimal=True)


class AngleConverter:
    regex = r"\d+(\.\d+)?\s?\w+"

    def to_python(self, value) -> float:
        return Angle(value).deg

    def to_url(self, value) -> str:
        return value.to_string()
