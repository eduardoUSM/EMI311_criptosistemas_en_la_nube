"""RF1, RNF1 y RNF4: entrada local y aleatoriedad criptográfica."""
import secrets
from .modelo import Parametros, Share


class Hospital:
    def __init__(self, i: int, x: int, par: Parametros):
        if type(i) is not int or not 1 <= i <= par.n:
            raise ValueError("hospital desconocido")
        if type(x) is not int or not 0 <= x <= par.M:
            raise ValueError("entrada fuera de [0,M] o no entera")
        self.i, self._x, self.par = i, x, par

    def compartir(self) -> tuple[Share, ...]:
        p = self.par.p
        if self.par.esquema == "shamir":
            # Se incluye a=0: excluirlo sesgaría la distribución del share.
            a = secrets.randbelow(p)
            valores = [(self._x + a*j) % p for j in range(1, 4)]
        else:
            valores = [secrets.randbelow(p) for _ in range(self.par.m - 1)]
            valores.append((self._x - sum(valores)) % p)
        return tuple(Share(self.par.sid, self.i, j, v)
                     for j, v in enumerate(valores, 1))
