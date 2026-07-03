"""
Metacognitive Evaluator — gradient quality self-assessment.

Inspired by Steiniger's prompt-induced metacognition:
each node evaluates whether its own training contribution
is worth submitting before broadcasting gradients.

Returns quality_score 0.0–1.0.
- Below 0.3: do not submit (saves bandwidth, doesn't corrupt model)
- 0.3–0.7:   submit with reduced weight
- Above 0.7: high-confidence gradient, maximum weight
"""

import math
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class MetacognitiveEvaluator:
    """
    Self-evaluates training quality before gradient submission.

    Uses three signals:
    1. Gradient norm health (exploding/vanishing detection)
    2. Validation loss improvement on held-out examples
    3. Perplexity bounds check
    """

    MIN_IMPROVEMENT_THRESHOLD = -0.5  # allow up to 50% degradation before hard reject

    def __init__(self, max_gradient_norm: float = 10.0, max_perplexity: float = 200.0):
        self.max_gradient_norm = max_gradient_norm
        self.max_perplexity = max_perplexity

    def evaluate(
        self,
        gradient_norm: float,
        val_loss_before: float,
        val_loss_after: float,
        perplexity: Optional[float] = None,
    ) -> float:
        """
        Compute quality score 0.0–1.0.

        Args:
            gradient_norm: L2 norm of the LoRA delta
            val_loss_before: cross-entropy loss on validation set before training
            val_loss_after: cross-entropy loss on validation set after training
            perplexity: model perplexity after training (computed from val_loss if None)

        Returns:
            quality_score in [0.0, 1.0]
        """
        if math.isnan(gradient_norm) or math.isinf(gradient_norm):
            logger.warning("Gradient is NaN/Inf — rejecting")
            return 0.0

        if gradient_norm > self.max_gradient_norm:
            logger.warning(f"Gradient norm {gradient_norm:.2f} > {self.max_gradient_norm} — rejecting")
            return 0.0

        if gradient_norm < 1e-8:
            logger.warning("Gradient vanished — rejecting")
            return 0.0

        if perplexity is None:
            try:
                perplexity = math.exp(val_loss_after)
            except OverflowError:
                perplexity = float('inf')

        if perplexity > self.max_perplexity:
            logger.warning(f"Perplexity {perplexity:.1f} > {self.max_perplexity} — low confidence")
            return 0.1

        if val_loss_before <= 0:
            improvement = 0.5
        else:
            improvement = (val_loss_before - val_loss_after) / val_loss_before

        if improvement < self.MIN_IMPROVEMENT_THRESHOLD:
            logger.warning(f"Loss degraded by {-improvement*100:.1f}% — rejecting")
            return 0.0

        norm_score = self._norm_quality(gradient_norm)
        raw_score = max(0.0, improvement) * 0.7 + norm_score * 0.3

        return round(min(1.0, max(0.0, raw_score)), 4)

    def quick_check(self, gradient_norm: float) -> bool:
        """Fast pre-check before expensive validation pass."""
        return (
            not math.isnan(gradient_norm)
            and not math.isinf(gradient_norm)
            and 1e-8 < gradient_norm < self.max_gradient_norm
        )

    def evaluate_from_ollama_response(
        self,
        baseline_response: Dict[str, Any],
        trained_response: Dict[str, Any],
        gradient_norm: float,
    ) -> float:
        """
        Evaluate quality using Ollama eval_duration as proxy for response confidence.
        Lower ns/token after training = model more confident = better quality.
        """
        try:
            baseline_tokens = baseline_response.get('eval_count', 0)
            trained_tokens = trained_response.get('eval_count', 0)
            baseline_duration = baseline_response.get('eval_duration', 1)
            trained_duration = trained_response.get('eval_duration', 1)

            if baseline_tokens == 0 or trained_tokens == 0:
                return self.evaluate(gradient_norm, 1.0, 1.0)

            baseline_ns_per_token = baseline_duration / baseline_tokens
            trained_ns_per_token = trained_duration / trained_tokens
            efficiency_improvement = (baseline_ns_per_token - trained_ns_per_token) / baseline_ns_per_token

            val_loss_proxy_before = math.log(max(baseline_tokens, 1))
            val_loss_proxy_after = math.log(max(trained_tokens, 1)) * (1 - efficiency_improvement * 0.1)

            return self.evaluate(gradient_norm, val_loss_proxy_before, val_loss_proxy_after)
        except Exception as e:
            logger.error(f"Ollama evaluation failed: {e}")
            return self.evaluate(gradient_norm, 1.0, 1.0)

    def _norm_quality(self, norm: float) -> float:
        """Maps gradient norm to quality score. Optimal range: 0.1–5.0"""
        if norm < 0.01:
            return 0.1
        elif norm < 0.1:
            return 0.5
        elif norm <= 5.0:
            return 1.0
        elif norm <= 10.0:
            return 0.5
        else:
            return 0.0


def evaluate_gradient(
    gradient_norm: float,
    val_loss_before: float,
    val_loss_after: float,
    perplexity: Optional[float] = None,
) -> float:
    return MetacognitiveEvaluator().evaluate(gradient_norm, val_loss_before, val_loss_after, perplexity)
