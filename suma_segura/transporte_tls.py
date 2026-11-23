"""Canal de laboratorio real TLS 1.3 mutuo; no es un despliegue multi-nube.

El receptor coteja el CN autenticado con el origen declarado del mensaje.
Los certificados son emitidos por la CA de prueba. La orquestación del
protocolo sigue usando la simulación; este módulo se prueba por separado.
"""
from dataclasses import asdict
import json
import ssl
import struct
from .modelo import Share, Parcial


def contexto_servidor(ca, certificado, clave):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_verify_locations(cafile=str(ca))
    ctx.load_cert_chain(str(certificado), str(clave))
    return ctx


def contexto_cliente(ca, certificado=None, clave=None):
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=str(ca))
    ctx.minimum_version = ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    if certificado:
        ctx.load_cert_chain(str(certificado), str(clave))
    return ctx


def _leer(sock, cantidad):
    datos = b""
    while len(datos) < cantidad:
        bloque = sock.recv(cantidad - len(datos))
        if not bloque:
            raise ConnectionError("mensaje incompleto")
        datos += bloque
    return datos


def enviar(sock, mensaje):
    if not isinstance(mensaje, (Share, Parcial)):
        raise ValueError("tipo de mensaje no permitido")
    datos = json.dumps({"tipo": type(mensaje).__name__, "datos": asdict(mensaje)},
                       separators=(",", ":")).encode("utf-8")
    if len(datos) > 4096:
        raise ValueError("mensaje demasiado grande")
    sock.sendall(struct.pack("!I", len(datos)) + datos)


def recibir(sock, tipo_esperado):
    if tipo_esperado not in (Share, Parcial):
        raise ValueError("tipo receptor no permitido")
    largo = struct.unpack("!I", _leer(sock, 4))[0]
    if not 0 < largo <= 4096:
        raise ValueError("tamaño de mensaje inválido")
    objeto = json.loads(_leer(sock, largo))
    if not isinstance(objeto, dict) or set(objeto) != {"tipo", "datos"}:
        raise ValueError("formato de mensaje inválido")
    if objeto["tipo"] != tipo_esperado.__name__ or not isinstance(objeto["datos"], dict):
        raise ValueError("tipo inesperado")
    mensaje = tipo_esperado(**objeto["datos"])
    indice = mensaje.origen if isinstance(mensaje, Share) else mensaje.servidor
    if type(indice) is not int:
        raise ValueError("identidad no entera")
    identidad = ("H" if isinstance(mensaje, Share) else "S") + str(indice)
    nombres = [v for bloque in sock.getpeercert().get("subject", ())
               for k, v in bloque if k == "commonName"]
    if nombres != [identidad]:
        raise PermissionError("identidad del certificado no coincide con el mensaje")
    return mensaje
