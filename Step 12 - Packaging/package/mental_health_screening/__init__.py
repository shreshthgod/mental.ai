"""Safety can be imported without loading optional legacy inference packages."""
__all__ = ["MentalHealthScreener"]


def __getattr__(name):
    if name == "MentalHealthScreener":
        from .inference import MentalHealthScreener
        return MentalHealthScreener
    raise AttributeError(name)
