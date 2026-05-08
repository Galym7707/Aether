"""Static analysis passes that run between parse and exec."""

from .effects import check_effects

__all__ = ["check_effects"]
