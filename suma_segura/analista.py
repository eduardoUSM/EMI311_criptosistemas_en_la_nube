"""RF3, RNF3: reconstrucción, umbral y consistencia limitada."""
from time import monotonic
from .modelo import Parametros, Parcial, Resultado, Pendiente, SesionAbortada


def reconstruir_par(u: int, yu: int, v: int, yv: int, p: int) -> int:
    """Interpolación de una recta en cero. El contrato exige cuerpo primo."""
    if u == v or u % p == 0 or v % p == 0:
        raise ValueError("abscisas distintas y no nulas")
    lu = v * pow(v-u, -1, p)
    lv = u * pow(u-v, -1, p)
    return (lu*yu + lv*yv) % p


class Analista:
    def __init__(self, par: Parametros, reloj=monotonic):
        self.par, self.reloj = par, reloj
        self.limite = reloj() + par.T
        self.parciales: dict[int, int] = {}
        self.eventos: list[str] = []
        self.cerrado = False

    def recibir(self, msg: Parcial) -> bool:
        if self.cerrado or self.reloj() >= self.limite:
            self.eventos.append("FUERA_DE_PLAZO_O_CERRADO")
            return False
        if (not isinstance(msg, Parcial) or msg.sid != self.par.sid
                or type(msg.servidor) is not int or not 1 <= msg.servidor <= self.par.m
                or type(msg.valor) is not int or not 0 <= msg.valor < self.par.p):
            self.eventos.append("PARCIAL_INVALIDO")
            return False
        if msg.servidor in self.parciales:
            self.eventos.append("DUPLICADO")
            return False
        self.parciales[msg.servidor] = msg.valor
        return True

    def reconstruir(self) -> Resultado:
        if self.cerrado:
            raise SesionAbortada("sesión cerrada")
        completo = len(self.parciales) == self.par.m
        if not completo and self.reloj() < self.limite:
            raise Pendiente("se espera hasta T para disponer de todos los parciales")
        self.cerrado = True
        ids = tuple(sorted(self.parciales))
        if self.par.esquema == "aditivo":
            if not completo:
                raise SesionAbortada("la base aditiva necesita todos los servidores")
            valor = sum(self.parciales.values()) % self.par.p
        else:
            if len(ids) < 2:
                raise SesionAbortada("menos de dos parciales")
            if completo:
                z1, z2, z3 = (self.parciales[j] for j in (1, 2, 3))
                if (z1 - 2*z2 + z3) % self.par.p:
                    self.eventos.append("INCONSISTENCIA")
                    raise SesionAbortada("parciales no colineales")
            u, v = ids[:2]
            valor = reconstruir_par(u, self.parciales[u], v, self.parciales[v], self.par.p)
        if not 0 <= valor <= self.par.n * self.par.M:
            raise SesionAbortada("resultado fuera de la cota pública")
        return Resultado(valor, not completo, ids)
