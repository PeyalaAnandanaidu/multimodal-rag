import re
import os
from dataclasses import dataclass, field
from typing import Optional

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"


@dataclass
class OutputGuardResult:
    is_safe:      bool
    answer:       str
    violations:   list[str]       = field(default_factory=list)
    warnings:     list[str]       = field(default_factory=list)
    was_modified: bool            = False
    metadata:     dict            = field(default_factory=dict)


# PII patterns to scrub from outputs
PII_SCRUB_PATTERNS = {
    "email":       (r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", "[EMAIL]"),
    "phone":       (r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]"),
    "ssn":         (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
    "api_key":     (r"\b(sk-|gsk_|AIza|AKIA)[A-Za-z0-9_\-]{16,}\b", "[API_KEY]"),
    "credit_card": (r"\b(?:\d[ -]?){13,16}\b", "[CARD]"),
}

# Hallucination markers
HALLUCINATION_PHRASES = [
    r"as\s+of\s+my\s+(knowledge|training)\s+cutoff",
    r"based\s+on\s+my\s+(general|broad|wide)\s+knowledge",
    r"i\s+(know|believe|think)\s+from\s+my\s+training",
    r"according\s+to\s+my\s+(knowledge|training|data)",
    r"in\s+general[,\s]+outside\s+(of\s+)?this\s+document",
    r"from\s+what\s+i\s+know\s+generally",
    r"based\s+on\s+my\s+understanding\s+(of\s+the\s+world|generally)",
]

# Toxic / harmful output patterns
TOXIC_PATTERNS = [
    r"\b(kill|murder|rape|terrorist|bomb\s+making)\b",
    r"step[s\-\s]+\d+[:\s]+.{0,50}(harmful|dangerous|illegal)",
]

# "I don't know" variants — valid responses
UNCERTAINTY_PHRASES = [
    "i don't know",
    "i do not know",
    "cannot find",
    "not mentioned",
    "not found in",
    "no information",
    "context doesn't",
    "context does not",
    "not available in",
]


class OutputGuardrail:
    """
    Post-generation output validation:
    1. Length validation
    2. PII scrubbing
    3. Hallucination detection
    4. Toxic content filtering
    5. Empty / refusal detection
    6. Source grounding check
    """

    def __init__(
        self,
        max_length:           int  = 8000,
        min_length:           int  = 10,
        scrub_pii:            bool = True,
        block_hallucinations: bool = True,
        block_toxic:          bool = True,
    ):
        self.max_length           = max_length
        self.min_length           = min_length
        self.scrub_pii            = scrub_pii
        self.block_hallucinations = block_hallucinations
        self.block_toxic          = block_toxic

        self._hallucination_re = [
            re.compile(p, re.IGNORECASE) for p in HALLUCINATION_PHRASES
        ]
        self._toxic_re = [
            re.compile(p, re.IGNORECASE) for p in TOXIC_PATTERNS
        ]
        self._pii_re = {
            name: (re.compile(pattern, re.IGNORECASE), replacement)
            for name, (pattern, replacement) in PII_SCRUB_PATTERNS.items()
        }

    # ──────────────────────────────────────────────────────
    def validate(
        self,
        answer:       str,
        query:        str        = "",
        sources:      list       = None,
        context_text: str        = ""
    ) -> OutputGuardResult:

        sources      = sources or []
        violations   = []
        warnings     = []
        was_modified = False
        modified     = answer

        # ── 1. Empty Answer ────────────────────────────
        if not answer or not answer.strip():
            return OutputGuardResult(
                is_safe=False,
                answer="I was unable to generate an answer. Please try again.",
                violations=["Empty response from LLM."],
                was_modified=True
            )

        # ── 2. Length Check ────────────────────────────
        if len(answer) < self.min_length:
            warnings.append("Response is very short.")

        if len(answer) > self.max_length:
            # Truncate gracefully at last sentence
            truncated  = answer[:self.max_length]
            last_punct = max(
                truncated.rfind('.'),
                truncated.rfind('!'),
                truncated.rfind('?')
            )
            if last_punct > self.max_length * 0.8:
                modified = truncated[:last_punct + 1] + "\n\n[Response truncated]"
            else:
                modified = truncated + "..."
            was_modified = True
            warnings.append(f"Response truncated from {len(answer)} to {self.max_length} chars.")

        # ── 3. Toxic Content ───────────────────────────
        if self.block_toxic:
            for pattern in self._toxic_re:
                if pattern.search(modified):
                    return OutputGuardResult(
                        is_safe=False,
                        answer="I cannot provide that information.",
                        violations=["Response contains harmful content."],
                        was_modified=True
                    )

        # ── 4. Hallucination Detection ─────────────────
        hallucination_markers = []
        if self.block_hallucinations:
            for pattern in self._hallucination_re:
                match = pattern.search(modified)
                if match:
                    hallucination_markers.append(match.group()[:60])

        if hallucination_markers:
            warnings.append(
                "Response may contain information beyond document context. "
                "Please verify with the source document."
            )
            # Add disclaimer instead of blocking
            modified = (
                modified +
                "\n\n> ⚠️ *Note: This answer may include general knowledge "
                "beyond the document. Please verify with the original source.*"
            )
            was_modified = True

        # ── 5. PII Scrubbing ───────────────────────────
        if self.scrub_pii:
            scrubbed_types = []
            for pii_type, (pattern, replacement) in self._pii_re.items():
                new_text, count = pattern.subn(replacement, modified)
                if count > 0:
                    modified      = new_text
                    was_modified  = True
                    scrubbed_types.append(pii_type)

            if scrubbed_types:
                warnings.append(
                    f"PII detected and redacted from response: {scrubbed_types}"
                )

        # ── 6. Grounding Check ─────────────────────────
        is_uncertain = any(
            phrase in modified.lower()
            for phrase in UNCERTAINTY_PHRASES
        )

        if sources and not is_uncertain:
            # Ensure answer doesn't completely ignore context
            if len(modified.split()) < 5:
                warnings.append(
                    "Response seems very brief. Consider rephrasing your question."
                )

        return OutputGuardResult(
            is_safe      = len(violations) == 0,
            answer       = modified,
            violations   = violations,
            warnings     = warnings,
            was_modified = was_modified,
            metadata     = {
                "hallucination_markers": hallucination_markers,
                "char_count":            len(modified),
                "word_count":            len(modified.split()),
                "is_uncertain":          is_uncertain,
            }
        )