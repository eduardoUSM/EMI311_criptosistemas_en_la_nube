"""T8 del E3: TLS real sobre socket local, separado de la simulación."""
import socket
import ssl
from threading import Thread
import pytest
from suma_segura import Share, Parcial
from suma_segura.transporte_tls import contexto_servidor, contexto_cliente, enviar, recibir


def intercambio(base, cliente, mensaje):
    contexto_s = contexto_servidor(base/"ca.crt", base/"servidor.crt", base/"servidor.key")
    contexto_c = contexto_cliente(base/"ca.crt",
        base/(cliente+".crt") if cliente else None,
        base/(cliente+".key") if cliente else None)
    crudo_s, crudo_c = socket.socketpair()
    crudo_s.settimeout(4); crudo_c.settimeout(4)
    estado = {}

    def servidor():
        try:
            with contexto_s.wrap_socket(crudo_s, server_side=True) as s:
                estado["version_servidor"] = s.version()
                estado["mensaje"] = recibir(s, type(mensaje))
                s.sendall(b"OK")
        except Exception as error:
            estado["error_servidor"] = error

    hilo = Thread(target=servidor, daemon=True)
    hilo.start()
    try:
        with contexto_c.wrap_socket(crudo_c, server_hostname="localhost") as c:
            estado["version_cliente"] = c.version()
            enviar(c, mensaje)
            estado["respuesta"] = c.recv(2)
    except Exception as error:
        estado["error_cliente"] = error
    finally:
        crudo_c.close()
        hilo.join(timeout=5)
        crudo_s.close()
    assert not hilo.is_alive(), "el laboratorio TLS no terminó"
    return estado


@pytest.mark.caso("T8")
@pytest.mark.requisito("RNF2")
@pytest.mark.parametrize("cliente,mensaje", [
    ("hospital",Share("sesion",1,1,22)),
    ("parcial",Parcial("sesion",1,22)),
])
def test_T8_TLS13_mutuo_valido(certificados,cliente,mensaje):
    estado = intercambio(certificados,cliente,mensaje)
    assert estado.get("mensaje") == mensaje
    assert estado.get("respuesta") == b"OK"
    assert estado["version_servidor"] == estado["version_cliente"] == "TLSv1.3"
    assert "error_servidor" not in estado and "error_cliente" not in estado


@pytest.mark.caso("T8")
@pytest.mark.requisito("RNF2")
@pytest.mark.parametrize("cliente,mensaje", [
    (None,Share("sesion",1,1,22)), (None,Parcial("sesion",1,22)),
    ("intruso",Share("sesion",1,1,22)), ("intruso",Parcial("sesion",1,22)),
])
def test_T8_sin_certificado_o_CA_ajena(certificados,cliente,mensaje):
    estado = intercambio(certificados,cliente,mensaje)
    assert isinstance(estado.get("error_servidor"),ssl.SSLError)
    assert "mensaje" not in estado


@pytest.mark.caso("X17")
@pytest.mark.requisito("RNF2")
@pytest.mark.parametrize("cliente,mensaje", [
    ("hospital",Share("sesion",2,1,22)),
    ("hospital",Parcial("sesion",1,22)),
    ("parcial",Share("sesion",1,1,22)),
])
def test_X17_certificado_no_autoriza_otro_origen(certificados,cliente,mensaje):
    estado = intercambio(certificados,cliente,mensaje)
    assert isinstance(estado.get("error_servidor"),PermissionError)
    assert "mensaje" not in estado
