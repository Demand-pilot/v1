"""
Model-layer exceptions for DemandPilot.

These exist so that a model which cannot produce a real answer fails loudly instead of
returning a plausible-looking default. A silent default from an unfitted model is
indistinguishable, downstream, from a genuine prediction — which is precisely how
`np.ones(n) * 100.0` ended up being served to the dashboard as a forecast.
"""


class ModelError(Exception):
    """Base class for all model-layer failures."""


class ModelNotFittedError(ModelError):
    """
    Raised when prediction is requested from a model that has not been fitted.

    Callers must handle this by surfacing an empty state, never by substituting a number.
    """


class FeatureSchemaMismatchError(ModelError):
    """
    Raised when an inference feature frame does not match the schema the model was
    trained on (missing columns, reordered columns, or a changed categorical vocabulary).

    Predicting through a mismatched schema is silently wrong rather than loudly wrong,
    so it is refused.
    """
