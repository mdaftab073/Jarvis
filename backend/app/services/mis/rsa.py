import base64
import re

from cryptography.hazmat.primitives.asymmetric import padding, rsa


class MISRSAError(ValueError):
    pass


def _integer(value: str, field: str) -> int:
    normalized = re.sub(r"\s+", "", value or "")
    if normalized.casefold().startswith("0x"):
        normalized = normalized[2:]
    if not normalized or not re.fullmatch(r"[0-9a-fA-F]+", normalized):
        raise MISRSAError(f"MIS RSA {field} is not valid hexadecimal")
    result = int(normalized, 16)
    if result <= 0:
        raise MISRSAError(f"MIS RSA {field} must be positive")
    return result


def build_rsa_key(modulus: str, exponent: str) -> rsa.RSAPublicKey:
    try:
        return rsa.RSAPublicNumbers(
            _integer(exponent, "exponent"),
            _integer(modulus, "modulus"),
        ).public_key()
    except ValueError as error:
        raise MISRSAError("MIS RSA public key is invalid") from error


def encrypt_password(
    password: str,
    modulus: str,
    exponent: str,
    encoding: str = "hex",
) -> str:
    """Encrypt as RSAES-PKCS1-v1_5, matching the common SVNIT JSBN browser client."""
    if not password:
        raise MISRSAError("MIS password must not be empty")
    key = build_rsa_key(modulus, exponent)
    try:
        ciphertext = key.encrypt(password.encode("utf-8"), padding.PKCS1v15())
    except ValueError as error:
        raise MISRSAError("MIS password is too long for the advertised RSA key") from error
    if encoding == "hex":
        return ciphertext.hex()
    if encoding == "base64":
        return base64.b64encode(ciphertext).decode("ascii")
    raise MISRSAError("MIS RSA ciphertext encoding must be 'hex' or 'base64'")
