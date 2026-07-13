# ============================================================
# Fix Windows OpenMP conflict — MUST be first
# ============================================================
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"]       = "1"

import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ============================================================
# Enums & Data Classes
# ============================================================
class RiskLevel(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    BLOCK  = "block"


@dataclass
class GuardResult:
    is_safe:    bool
    risk_level: RiskLevel        = RiskLevel.LOW
    violations: list             = field(default_factory=list)
    warnings:   list             = field(default_factory=list)
    sanitized:  Optional[str]    = None
    metadata:   dict             = field(default_factory=dict)


# ============================================================
# Patterns
# ============================================================

# Prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all|prior)\s+(instructions?|prompts?|context|rules?)",
    r"forget\s+(everything|all|previous|above|your\s+instructions?)",
    r"you\s+are\s+now\s+(a\s+)?(different|new|another|evil|bad|harmful)",
    r"(act|behave|pretend|roleplay|imagine)\s+(as\s+)?(if\s+)?(you\s+are|you're|being)",
    r"disregard\s+(all\s+)?(previous|prior|above|your)",
    r"new\s+(instructions?|rules?|persona|role|task)",
    r"system\s*:\s*(you\s+are|ignore|forget|new)",
    r"<\s*system\s*>",
    r"\[INST\]|\[\/INST\]",
    r"###\s*(instruction|system|human|assistant)\s*:",
    r"override\s+(safety|guidelines?|rules?|restrictions?)",
    r"jailbreak|DAN\s+mode|developer\s+mode",
]

# PII patterns
PII_PATTERNS = {
    "email":       r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    "phone_us":    r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "ssn":         r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d[ -]?){13,16}\b",
    "api_key":     r"\b(sk-|gsk_|AIza|AKIA)[A-Za-z0-9_\-]{16,}\b",
    "ip_address":  r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
}

# Harmful content
HARMFUL_KEYWORDS = [
    "how to make a bomb", "synthesize drugs", "create malware",
    "hack into", "bypass security", "create virus",
    "make explosives", "illegal weapons", "child exploitation",
    "self-harm instructions",
]

# Hard-block off-topic patterns
OFF_TOPIC_HARD_BLOCK = [
    r"(generate|create|make)\s+(fake|false)\s+(news|information|data|reports?)",
    r"(tell\s+me\s+(about|how)|explain\s+how)\s+(to\s+)?(hack|steal|cheat|fraud)",
]

# ============================================================
# Query enrichment keyword maps
# ============================================================

# Maps detected topic → enriched question template
ENRICHMENT_MAP = [
    # Contact / PII topics
    (
        ["email", "mail", "e-mail"],
        "What is the email address mentioned in the document?"
    ),
    (
        ["phone", "mobile", "contact number", "telephone"],
        "What is the phone number or contact information mentioned in the document?"
    ),
    (
        ["contact", "contact info", "contact details", "contact information"],
        "What are the contact details mentioned in the document?"
    ),
    (
        ["address", "location", "city", "state", "country"],
        "What is the address or location information mentioned in the document?"
    ),
    (
        ["linkedin", "github", "portfolio", "website", "url", "link"],
        "What are the online profiles or links mentioned in the document?"
    ),

    # Personal info topics
    (
        ["personal info", "personal information", "personal details",
         "personal profile", "bio", "biography", "about him", "about her",
         "about them", "about the person", "about me"],
        "What is the personal information about the person described in the document?"
    ),
    (
        ["name", "full name", "person name"],
        "What is the name of the person mentioned in the document?"
    ),

    # Professional topics
    (
        ["project", "projects", "work done", "work on", "built", "developed",
         "created", "made"],
        "List all the projects mentioned in the document with their descriptions."
    ),
    (
        ["skill", "skills", "technology", "technologies", "tools",
         "tech stack", "programming", "languages", "frameworks"],
        "What are the technical skills and technologies mentioned in the document?"
    ),
    (
        ["experience", "work experience", "job", "jobs", "career",
         "employment", "worked at", "company", "companies",
         "organization", "organisations"],
        "What is the work experience or employment history mentioned in the document?"
    ),
    (
        ["education", "degree", "university", "college", "school",
         "qualification", "graduation", "gpa", "cgpa", "marks",
         "certification", "certifications"],
        "What is the educational background and qualifications mentioned in the document?"
    ),
    (
        ["achievement", "achievements", "award", "awards", "recognition",
         "accomplishment", "accomplishments", "honor", "honours"],
        "What achievements or awards are mentioned in the document?"
    ),
    (
        ["summary", "overview", "profile", "introduction", "objective",
         "about", "description"],
        "What is the overall summary or profile described in the document?"
    ),
    (
        ["publication", "publications", "research", "paper", "papers",
         "journal", "article", "articles"],
        "What publications or research work is mentioned in the document?"
    ),
    (
        ["language", "languages", "spoken", "written", "fluent"],
        "What languages are mentioned in the document?"
    ),
    (
        ["salary", "compensation", "ctc", "package"],
        "What salary or compensation information is mentioned in the document?"
    ),

    # Document structure topics
    (
        ["chart", "charts", "graph", "graphs", "image", "images",
         "figure", "figures", "diagram", "diagrams", "visual", "visuals",
         "table", "tables", "plot", "plots"],
        "What charts, graphs, images, or visual elements are present in the document and what do they show?"
    ),
    (
        ["finding", "findings", "result", "results", "conclusion",
         "conclusions", "insight", "insights", "key point", "key points",
         "takeaway", "takeaways"],
        "What are the main findings, results, or conclusions in the document?"
    ),
    (
        ["revenue", "sales", "profit", "loss", "financial", "finance",
         "quarter", "quarterly", "annual", "yearly", "growth"],
        "What financial information or revenue trends are described in the document?"
    ),
]

# Question starters that indicate query is already well-formed
QUESTION_STARTERS = {
    "what", "who", "where", "when", "why", "how", "which",
    "list", "show", "tell", "give", "find", "get",
    "summarize", "describe", "explain", "compare", "analyze",
    "is", "are", "was", "were", "does", "do", "did",
    "can", "could", "would", "should", "has", "have", "had",
    "extract", "identify", "mention", "provide", "name"
}


# ============================================================
# InputGuardrail Class
# ============================================================
class InputGuardrail:
    """
    Multi-layer input validation + query enrichment:

    Validation layers:
      1. Length check
      2. Prompt injection detection
      3. Harmful content detection
      4. Hard off-topic block
      5. PII detection (warn, not block)
      6. Sanitization

    Enrichment:
      7. Convert vague noun-phrases to proper questions
    """

    def __init__(
        self,
        max_length:  int  = 2000,
        min_length:  int  = 2,
        allow_pii:   bool = False,
        strict_mode: bool = True,
    ):
        self.max_length  = max_length
        self.min_length  = min_length
        self.allow_pii   = allow_pii
        self.strict_mode = strict_mode

        # Compile all patterns once at init
        self._injection_re = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in INJECTION_PATTERNS
        ]
        self._pii_re = {
            name: re.compile(p, re.IGNORECASE)
            for name, p in PII_PATTERNS.items()
        }
        self._harmful_re = re.compile(
            "|".join(re.escape(k) for k in HARMFUL_KEYWORDS),
            re.IGNORECASE
        )
        self._offtopic_re = [
            re.compile(p, re.IGNORECASE)
            for p in OFF_TOPIC_HARD_BLOCK
        ]

    # ──────────────────────────────────────────────────────
    # PUBLIC: validate only
    # ──────────────────────────────────────────────────────
    def validate(
        self,
        query:  str,
        pdf_id: Optional[str] = None
    ) -> GuardResult:
        """
        Validate a query through all safety layers.
        Returns GuardResult with is_safe=False if blocked.
        """
        violations = []
        warnings   = []
        metadata   = {}

        stripped = query.strip()

        # ── 1. Empty / Length ──────────────────────────
        if not stripped:
            return GuardResult(
                is_safe    = False,
                risk_level = RiskLevel.BLOCK,
                violations = ["Query is empty."],
                sanitized  = None,
            )

        if len(stripped) < self.min_length:
            return GuardResult(
                is_safe    = False,
                risk_level = RiskLevel.BLOCK,
                violations = [
                    f"Query too short (min {self.min_length} characters)."
                ],
                sanitized  = None,
            )

        if len(stripped) > self.max_length:
            return GuardResult(
                is_safe    = False,
                risk_level = RiskLevel.BLOCK,
                violations = [
                    f"Query too long ({len(stripped)} chars). "
                    f"Maximum allowed: {self.max_length}."
                ],
                sanitized  = None,
            )

        # ── 2. Prompt Injection ────────────────────────
        injection_hits = []
        for pattern in self._injection_re:
            match = pattern.search(stripped)
            if match:
                injection_hits.append(match.group()[:60])

        if injection_hits:
            return GuardResult(
                is_safe    = False,
                risk_level = RiskLevel.BLOCK,
                violations = [
                    f"Prompt injection detected: '{hit}'"
                    for hit in injection_hits[:3]
                ],
                metadata   = {"injection_patterns": injection_hits},
                sanitized  = None,
            )

        # ── 3. Harmful Content ─────────────────────────
        if self._harmful_re.search(stripped):
            return GuardResult(
                is_safe    = False,
                risk_level = RiskLevel.BLOCK,
                violations = ["Query contains harmful content."],
                sanitized  = None,
            )

        # ── 4. Hard Off-Topic Block ────────────────────
        for pattern in self._offtopic_re:
            if pattern.search(stripped):
                return GuardResult(
                    is_safe    = False,
                    risk_level = RiskLevel.BLOCK,
                    violations = [
                        "Query contains disallowed content. "
                        "Please ask questions about the document."
                    ],
                    sanitized  = None,
                )

        # ── 5. PII Detection (warn only, don't block) ──
        pii_found = {}
        for pii_type, pattern in self._pii_re.items():
            matches = pattern.findall(stripped)
            if matches:
                pii_found[pii_type] = len(matches)

        if pii_found:
            warnings.append(
                f"Query may contain sensitive information "
                f"({', '.join(pii_found.keys())}). "
                f"This will not be stored."
            )
            metadata["pii_detected"] = pii_found

        # ── 6. Sanitize ────────────────────────────────
        sanitized = self._sanitize(stripped)

        # ── Determine Risk Level ───────────────────────
        if pii_found:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.LOW

        return GuardResult(
            is_safe    = True,
            risk_level = risk,
            violations = violations,
            warnings   = warnings,
            sanitized  = sanitized,
            metadata   = metadata,
        )

    # ──────────────────────────────────────────────────────
    # PUBLIC: validate + enrich (used by main.py)
    # ──────────────────────────────────────────────────────
    def validate_and_enrich(
        self,
        query:  str,
        pdf_id: Optional[str] = None
    ) -> GuardResult:
        """
        Run full validation, then enrich vague queries
        into proper questions.

        Example enrichments:
          "his email"      → "What is the email address mentioned in the document?"
          "projects"       → "List all the projects mentioned in the document..."
          "his skills"     → "What are the technical skills and technologies..."
          "personal info"  → "What is the personal information about the person..."
        """
        # Step 1: Validate first
        result = self.validate(query, pdf_id)

        # Step 2: Only enrich if safe
        if result.is_safe and result.sanitized:
            original  = result.sanitized
            enriched  = self._enrich_query(original)
            result.sanitized = enriched

            # Add info warning if enriched
            if enriched != original:
                result.warnings.append(
                    f"Query was enriched for clarity: \"{enriched}\""
                )

        return result

    # ──────────────────────────────────────────────────────
    # PRIVATE: sanitize raw text
    # ──────────────────────────────────────────────────────
    def _sanitize(self, text: str) -> str:
        """Remove control chars, normalize whitespace."""
        # Remove null bytes and non-printable control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        # Collapse multiple spaces/tabs/newlines into single space
        text = re.sub(r'\s+', ' ', text).strip()
        # Reduce excessive repeated punctuation (e.g. "???" → "??")
        text = re.sub(r'([!?.]){3,}', r'\1\1', text)
        return text

    # ──────────────────────────────────────────────────────
    # PRIVATE: enrich vague noun-phrase queries
    # ──────────────────────────────────────────────────────
    def _enrich_query(self, query: str) -> str:
        """
        Convert short noun-phrase queries into full questions.

        Logic:
        1. If query already starts with a question word → return as-is
        2. If query ends with '?' → return as-is
        3. Otherwise → match against enrichment map → return template
        4. If no match → wrap in generic template
        """
        q         = query.strip()
        q_lower   = q.lower()
        words     = q_lower.split()
        first_word = words[0] if words else ""

        # Already a proper question
        if q.endswith("?"):
            return q

        # Starts with a known question/command word
        if first_word in QUESTION_STARTERS:
            return q

        # ── Match against enrichment map ───────────────
        for keywords, template in ENRICHMENT_MAP:
            for keyword in keywords:
                # Match keyword as substring
                if keyword in q_lower:
                    return template

        # ── Generic fallback ───────────────────────────
        # e.g. "quarterly performance" → "What does the document say about quarterly performance?"
        return f"What does the document say about {q}?"