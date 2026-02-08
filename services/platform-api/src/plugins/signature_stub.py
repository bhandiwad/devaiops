from __future__ import annotations

from adapters.interfaces import SignatureVerifierAdapter, VerificationResult


class StubSignatureVerifier(SignatureVerifierAdapter):
    """Stub signature verifier adapter."""

    def verify(self, image_ref: str) -> VerificationResult:
        return VerificationResult(status="unknown", detail={"image": image_ref})
