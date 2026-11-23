"""RF2: recepción por sesión, vista por hospital y emisión única."""
from enum import Enum
from time import monotonic
from .modelo import Parametros, Share, Parcial, Pendiente, SesionAbortada


class Estado(str, Enum):
    INACTIVO = "INACTIVO"
    RECIBIENDO = "RECIBIENDO"
    AGREGANDO = "AGREGANDO"
    ENVIADO = "ENVIADO"
    ABORTADO = "ABORTADO"


class Servidor:
    def __init__(self, j: int, par: Parametros, reloj=monotonic):
        if type(j) is not int or not 1 <= j <= par.m:
            raise ValueError("servidor desconocido")
        self.j, self.par, self.reloj = j, par, reloj
        self.limite = reloj() + par.T
        self.vista: dict[tuple[str, int], int] = {}
        self.eventos: list[str] = []  # Solo códigos, nunca shares en el log.
        self.historial = [Estado.INACTIVO, Estado.RECIBIENDO]
        self.estado = Estado.RECIBIENDO

    def _estado(self, estado):
        self.estado = estado
        self.historial.append(estado)

    def recibir(self, sh: Share) -> bool:
        # La identidad criptográfica se verifica en transporte_tls, no aquí.
        if self.estado != Estado.RECIBIENDO or self.reloj() >= self.limite:
            self.eventos.append("FUERA_DE_PLAZO_O_CERRADO")
            return False
        if not isinstance(sh, Share) or sh.sid != self.par.sid:
            self.eventos.append("SESION_INVALIDA")
            return False
        if (type(sh.origen) is not int or not 1 <= sh.origen <= self.par.n
                or type(sh.destino) is not int or sh.destino != self.j
                or type(sh.valor) is not int or not 0 <= sh.valor < self.par.p):
            self.eventos.append("MENSAJE_INVALIDO")
            return False
        clave = (sh.sid, sh.origen)
        if clave in self.vista:
            self.eventos.append("DUPLICADO")
            return False
        self.vista[clave] = sh.valor
        return True

    def agregar(self) -> Parcial:
        if self.estado != Estado.RECIBIENDO:
            raise SesionAbortada("servidor cerrado; no hay segunda emisión")
        if len(self.vista) != self.par.n:
            if self.reloj() < self.limite:
                raise Pendiente("faltan hospitales y aún no vence T")
            self._estado(Estado.ABORTADO)
            faltan = sorted(set(range(1, self.par.n + 1)) - {i for _, i in self.vista})
            raise SesionAbortada(f"faltan hospitales {faltan}")
        self._estado(Estado.AGREGANDO)
        parcial = Parcial(self.par.sid, self.j, sum(self.vista.values()) % self.par.p)
        self._estado(Estado.ENVIADO)
        return parcial
