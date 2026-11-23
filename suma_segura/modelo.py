"""Parámetros públicos y mensajes del caso académico EMI311."""
from dataclasses import dataclass
from math import isfinite, isqrt


def es_primo(p: int) -> bool:
    return type(p) is int and p >= 2 and all(p % d for d in range(2, isqrt(p) + 1))


@dataclass(frozen=True)
class Parametros:
    sid: str = "emi311-demo"
    n: int = 3
    m: int = 3
    M: int = 40
    p: int = 127
    T: float = 10.0
    esquema: str = "shamir"

    def __post_init__(self):
        if not isinstance(self.sid, str) or not 1 <= len(self.sid) <= 64:
            raise ValueError("sid debe ser una cadena no vacía de hasta 64 caracteres")
        if any(type(v) is not int for v in (self.n, self.m, self.M, self.p)):
            raise ValueError("n, m, M y p deben ser enteros")
        if self.n < 2 or self.m < 2 or self.M < 0 or self.p <= self.n * self.M:
            raise ValueError("se requiere n,m >= 2, M >= 0 y p > n*M")
        if type(self.T) not in (int, float) or not isfinite(self.T) or self.T <= 0:
            raise ValueError("T debe ser positivo y finito")
        if self.esquema not in ("aditivo", "shamir"):
            raise ValueError("esquema desconocido")
        if self.esquema == "shamir" and (self.m != 3 or self.p <= 3 or not es_primo(self.p)):
            raise ValueError("esta extensión requiere m=3 y p primo mayor que 3")


@dataclass(frozen=True)
class Share:
    sid: str
    origen: int
    destino: int
    valor: int


@dataclass(frozen=True)
class Parcial:
    sid: str
    servidor: int
    valor: int


@dataclass(frozen=True)
class Resultado:
    valor: int
    degradado: bool
    servidores: tuple[int, ...]


class SesionAbortada(Exception):
    pass


class Pendiente(Exception):
    pass
