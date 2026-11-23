"""Simulación local sin red. Las vistas contienen solo datos sintéticos."""
from .modelo import Parametros
from .hospital import Hospital
from .servidor import Servidor
from .analista import Analista


class RelojManual:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def avanzar(self, segundos):
        if segundos < 0:
            raise ValueError("el reloj no retrocede")
        self.t += segundos


def ejecutar(entradas, par=None, caidos=()):
    par = par or Parametros()
    if len(entradas) != par.n:
        raise ValueError("se requiere una entrada por hospital")
    if any(type(j) is not int or not 1 <= j <= par.m for j in caidos):
        raise ValueError("servidor caído desconocido")
    reloj = RelojManual()
    servidores = {j: Servidor(j, par, reloj) for j in range(1, par.m + 1)}
    hospitales = [Hospital(i, x, par) for i, x in enumerate(entradas, 1)]
    analista = Analista(par, reloj)
    for hospital in hospitales:
        for share in hospital.compartir():
            if share.destino not in caidos:
                servidores[share.destino].recibir(share)
    for j, servidor in servidores.items():
        if j not in caidos:
            analista.recibir(servidor.agregar())
    if caidos:
        reloj.avanzar(par.T)
    return analista.reconstruir(), servidores, analista
