import uuid
import hashlib

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def base62_encode(num: int) -> str:
    """Convert a large integer to a Base62 string."""
    if num == 0:
        return ALPHABET[0]
    result = []
    while num:
        result.append(ALPHABET[num % 62])
        num //= 62
    return "".join(reversed(result))

def generate_short_code() -> str:
    """
    Generate a unique 7-character short code.
    Uses UUID4 (cryptographically random) as the source integer.
    No clock dependency — works perfectly on Windows.
    """
    uid = uuid.uuid4().int          # 128-bit random integer
    code = base62_encode(uid)
    return code[:7]

def hash_long_url(long_url: str) -> str:
    """MD5 hash of the long URL — used for deduplication."""
    return hashlib.md5(long_url.encode()).hexdigest()