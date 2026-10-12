"""Safety can be imported without loading optional legacy inference packages."""
__all__ = ["MentalHealthScreener", "EmotionRecognizer", "EmotionAnalysis"]


def __getattr__(name):
    if name == "MentalHealthScreener":
        from .inference import MentalHealthScreener
        return MentalHealthScreener
    if name in ("EmotionRecognizer", "EmotionAnalysis"):
        from .emotion import EmotionRecognizer, EmotionAnalysis
        return EmotionRecognizer if name == "EmotionRecognizer" else EmotionAnalysis
    raise AttributeError(name)
