import pytest

from vizu_auth.core.exceptions import (
    InvalidSignatureError,
    InvalidTokenError,
    TokenExpiredError,
)
from vizu_auth.core.jwt_decoder import decode_jwt, validate_jwt
from vizu_auth.core.models import JWTClaims


class TestDecodeJWT:
    def test_decode_valid_token(self, valid_jwt_token, sample_external_user_id, sample_cliente_vizu_id):
        claims = decode_jwt(valid_jwt_token)
        assert isinstance(claims, JWTClaims)
        assert claims.sub == sample_external_user_id
        assert claims.email == "test@example.com"
        assert claims.cliente_vizu_id == sample_cliente_vizu_id

    def test_decode_token_with_bearer_prefix(self, valid_jwt_token):
        token_with_prefix = f"Bearer {valid_jwt_token}"
        claims = decode_jwt(token_with_prefix)
        assert isinstance(claims, JWTClaims)

    def test_decode_expired_token_raises_error(self, expired_jwt_token):
        with pytest.raises(TokenExpiredError):
            decode_jwt(expired_jwt_token)

    def test_decode_expired_token_with_verify_false(self, expired_jwt_token):
        claims = decode_jwt(expired_jwt_token, verify_exp=False)
        assert isinstance(claims, JWTClaims)

    def test_decode_invalid_signature_raises_error(self, invalid_signature_token):
        with pytest.raises(InvalidSignatureError):
            decode_jwt(invalid_signature_token)

    def test_decode_malformed_token_raises_error(self):
        with pytest.raises(InvalidTokenError):
            decode_jwt("not.a.valid.jwt")

    def test_decode_empty_token_raises_error(self):
        with pytest.raises(InvalidTokenError):
            decode_jwt("")


class TestValidateJWT:
    def test_validate_valid_token_returns_true(self, valid_jwt_token):
        assert validate_jwt(valid_jwt_token) is True

    def test_validate_expired_token_returns_false(self, expired_jwt_token):
        assert validate_jwt(expired_jwt_token) is False

    def test_validate_invalid_token_returns_false(self):
        assert validate_jwt("invalid") is False
