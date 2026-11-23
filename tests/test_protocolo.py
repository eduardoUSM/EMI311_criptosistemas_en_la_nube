from dataclasses import FrozenInstanceError, replace
import random
import pytest
from suma_segura import Parametros, Share, Parcial, Pendiente, SesionAbortada, ejecutar
from suma_segura.hospital import Hospital
from suma_segura.servidor import Servidor, Estado
from suma_segura.analista import Analista, reconstruir_par
from suma_segura.simulacion import RelojManual


@pytest.mark.caso("T1")
@pytest.mark.requisito("RF1,RF2,RF3")
def test_T1_mil_entradas():
    # La semilla reproduce los vectores de prueba, nunca los secretos.
    vectores = random.Random(311)
    for _ in range(1000):
        xs = [vectores.randrange(41) for _ in range(3)]
        resultado, servidores, _ = ejecutar(xs)
        assert resultado.valor == sum(xs)
        assert not resultado.degradado
        assert all(len(s.vista) == 3 for s in servidores.values())


@pytest.mark.caso("T2")
@pytest.mark.requisito("RF3,RNF4")
def test_T2_maximos():
    assert ejecutar([40, 40, 40])[0].valor == 120


@pytest.mark.caso("T3")
@pytest.mark.requisito("RF1,RF3,RNF1")
def test_T3_ceros_y_pendiente_cero(monkeypatch):
    assert ejecutar([0, 0, 0])[0].valor == 0
    monkeypatch.setattr("suma_segura.hospital.secrets.randbelow", lambda p: 0)
    mensajes = Hospital(1, 0, Parametros()).compartir()
    assert [s.valor for s in mensajes] == [0, 0, 0]
    assert ejecutar([0, 0, 0])[0].valor == 0


@pytest.mark.caso("T4")
@pytest.mark.requisito("RNF4")
@pytest.mark.parametrize("cambio", [{"p":121}, {"p":97}, {"p":120}, {"p":True},
    {"n":1}, {"m":2}, {"m":4}, {"M":-1}, {"n":2.5}, {"T":0}, {"T":float("nan")}, {"sid":""}])
def test_T4_parametros_invalidos(cambio):
    with pytest.raises(ValueError):
        Parametros(**cambio)


@pytest.mark.caso("T5")
@pytest.mark.requisito("RNF4")
@pytest.mark.parametrize("x", [41, -1, 12.5, True, "12"])
def test_T5_entrada_invalida(x):
    with pytest.raises(ValueError):
        Hospital(1, x, Parametros())


@pytest.mark.caso("T6")
@pytest.mark.requisito("RF2")
def test_T6_duplicado_no_cambia_vista_ni_emite_dos_veces():
    p = Parametros()
    s = Servidor(1, p)
    mensajes = [Hospital(i, x, p).compartir()[0] for i, x in enumerate([12,23,31], 1)]
    assert s.recibir(mensajes[0])
    assert not s.recibir(mensajes[0])
    assert not s.recibir(replace(mensajes[0], valor=(mensajes[0].valor+1)%p.p))
    assert len(s.vista) == 1
    for msg in mensajes[1:]:
        assert s.recibir(msg)
    assert s.agregar().valor == sum(m.valor for m in mensajes) % p.p
    assert s.historial == [Estado.INACTIVO, Estado.RECIBIENDO, Estado.AGREGANDO, Estado.ENVIADO]
    assert not s.recibir(mensajes[0])
    with pytest.raises(SesionAbortada):
        s.agregar()


@pytest.mark.caso("T7")
@pytest.mark.requisito("RNF2,RNF3")
def test_T7_sesion_cruzada_y_expirada():
    p = Parametros()
    reloj = RelojManual()
    s = Servidor(1, p, reloj)
    assert not s.recibir(Share("otra", 1, 1, 5))
    assert s.eventos == ["SESION_INVALIDA"]
    reloj.avanzar(p.T)
    assert not s.recibir(Share(p.sid, 1, 1, 5))
    with pytest.raises(SesionAbortada, match="faltan hospitales"):
        s.agregar()
    assert s.estado == Estado.ABORTADO


@pytest.mark.caso("T9")
@pytest.mark.requisito("RNF1")
def test_T9_uniformidad_10000(request):
    p, N, bins = 127, 10000, 10
    hospital = Hospital(1, 15, Parametros())
    observados = [0]*bins
    for _ in range(N):
        observados[bins * hospital.compartir()[0].valor // p] += 1
    tamanos = [sum(bins*v//p == b for v in range(p)) for b in range(bins)]
    esperados = [N*t/p for t in tamanos]
    chi2 = sum((o-e)**2/e for o, e in zip(observados, esperados))
    request.config.estadistica.update(N=N, x=15, p=p, intervalos=bins, gl=9,
        alfa=0.001, critico=27.88, chi2=chi2, observados=observados, esperados=esperados)
    assert chi2 < 27.88, "posible sesgo o falso rechazo; conservar evidencia e investigar"


@pytest.mark.caso("T10")
@pytest.mark.requisito("RF3,RNF3")
def test_T10_caida_S2():
    resultado, _, _ = ejecutar([12,23,31], caidos=(2,))
    assert resultado.valor == 66
    assert resultado.degradado and resultado.servidores == (1,3)


@pytest.mark.caso("T11")
@pytest.mark.requisito("RF3")
def test_T11_z2_alterado():
    p = Parametros()
    a = Analista(p)
    for j,z in [(1,22), (2,108), (3,61)]:
        assert a.recibir(Parcial(p.sid, j, z))
    with pytest.raises(SesionAbortada, match="no colineales"):
        a.reconstruir()
    assert "INCONSISTENCIA" in a.eventos


@pytest.mark.caso("X1")
@pytest.mark.requisito("RF1,RF2,RF3,RNF4")
def test_X1_ejemplo_E3_completo(monkeypatch):
    pendientes = iter([25,40,18])
    monkeypatch.setattr("suma_segura.hospital.secrets.randbelow", lambda p: next(pendientes))
    salida, servidores, analista = ejecutar([12,23,31])
    assert [[servidores[j].vista[("emi311-demo",i)] for j in (1,2,3)] for i in (1,2,3)] == [
        [37,62,87], [63,103,16], [49,67,85]]
    assert analista.parciales == {1:22, 2:105, 3:61}
    assert salida.valor == 66


@pytest.mark.caso("X2")
@pytest.mark.requisito("RF3,RNF3")
@pytest.mark.parametrize("caido", [1,2,3])
def test_X2_cualquier_par(caido):
    for xs in ([12,23,31], [40,40,40], [0,0,0]):
        r, _, _ = ejecutar(xs, caidos=(caido,))
        assert r.valor == sum(xs) and r.degradado


@pytest.mark.caso("X3")
@pytest.mark.requisito("RF3,RNF3")
@pytest.mark.parametrize("caidos", [(1,2), (1,3), (2,3), (1,2,3)])
def test_X3_dos_o_tres_caidos(caidos):
    with pytest.raises(SesionAbortada, match="menos de dos"):
        ejecutar([12,23,31], caidos=caidos)


@pytest.mark.caso("X4")
@pytest.mark.requisito("RNF1")
def test_X4_privacidad_de_un_share_enumeracion_exhaustiva():
    # Verifica la biyección del argumento matemático; no reemplaza su prueba.
    for x in range(41):
        for j in (1,2,3):
            valores = [(x+a*j)%127 for a in range(127)]
            assert sorted(valores) == list(range(127))


@pytest.mark.caso("X5")
@pytest.mark.requisito("RNF1")
def test_X5_dos_servidores_revelan_cada_entrada():
    p = Parametros()
    for i,x in enumerate([12,23,31], 1):
        s1,s2,_ = Hospital(i,x,p).compartir()
        assert reconstruir_par(1,s1.valor,2,s2.valor,p.p) == x


@pytest.mark.caso("X6")
@pytest.mark.requisito("RF3")
def test_X6_dos_parciales_no_detectan_manipulacion():
    p, reloj = Parametros(), RelojManual()
    a = Analista(p,reloj)
    a.recibir(Parcial(p.sid,1,22))
    a.recibir(Parcial(p.sid,2,108))
    reloj.avanzar(p.T)
    salida = a.reconstruir()
    assert salida.valor == 63 != 66 and salida.degradado


@pytest.mark.caso("X7")
@pytest.mark.requisito("RF3")
def test_X7_dos_alteraciones_coordinadas_pasan_colinealidad():
    # Δz=(0,1,2) mantiene la recta pero cambia la ordenada en -1.
    p, a = Parametros(), Analista(Parametros())
    for j,z in [(1,22),(2,106),(3,63)]:
        a.recibir(Parcial(p.sid,j,z))
    assert a.reconstruir().valor == 65 != 66


@pytest.mark.caso("X8")
@pytest.mark.requisito("RF1,RF2,RF3,RNF4")
@pytest.mark.parametrize("n,m,M,p", [(2,2,40,81),(3,3,40,121),(4,5,10,41),(5,4,0,2)])
def test_X8_base_aditiva_varia_n_m(n,m,M,p):
    par = Parametros(n=n,m=m,M=M,p=p,esquema="aditivo")
    for xs in ([M]*n, [0]*n):
        assert ejecutar(xs,par)[0].valor == sum(xs)


@pytest.mark.caso("X9")
@pytest.mark.requisito("RF1,RF2,RF3,RNF4")
@pytest.mark.parametrize("n,M,p", [(2,40,83),(4,10,43),(3,1000,3001),(5,0,5)])
def test_X9_shamir_varia_n_y_cotas(n,M,p):
    par = Parametros(n=n,M=M,p=p)
    assert ejecutar([M]*n,par)[0].valor == n*M


@pytest.mark.caso("X10")
@pytest.mark.requisito("RNF3")
def test_X10_base_aditiva_no_tolera_caida():
    with pytest.raises(SesionAbortada, match="necesita todos"):
        ejecutar([12,23,31],Parametros(p=121,esquema="aditivo"), caidos=(2,))


@pytest.mark.caso("X11")
@pytest.mark.requisito("RF2,RF3,RNF2,RNF4")
def test_X11_validacion_mensajes_y_parciales():
    p = Parametros()
    s, a = Servidor(1,p), Analista(p)
    for sh in [Share(p.sid,0,1,5), Share(p.sid,4,1,5),Share(p.sid,1,2,5),
               Share(p.sid,1,1,-1),Share(p.sid,1,1,127),Share(p.sid,True,1,5),Share(p.sid,1,1,2.5)]:
        assert not s.recibir(sh)
    for msg in [Parcial("otra",1,5),Parcial(p.sid,0,5),Parcial(p.sid,4,5),
                Parcial(p.sid,1,-1),Parcial(p.sid,1,127),Parcial(p.sid,True,5)]:
        assert not a.recibir(msg)
    assert not s.vista and not a.parciales
    assert a.recibir(Parcial(p.sid,1,5))
    assert not a.recibir(Parcial(p.sid,1,7))
    assert a.parciales == {1:5}


@pytest.mark.caso("X12")
@pytest.mark.requisito("RF3,RNF3")
def test_X12_no_publica_antes_del_plazo():
    p,reloj = Parametros(),RelojManual()
    a = Analista(p,reloj)
    a.recibir(Parcial(p.sid,1,22)); a.recibir(Parcial(p.sid,3,61))
    with pytest.raises(Pendiente):
        a.reconstruir()
    reloj.avanzar(p.T)
    assert not a.recibir(Parcial(p.sid,2,105))
    assert a.reconstruir().valor == 66
    with pytest.raises(SesionAbortada):
        a.reconstruir()


@pytest.mark.caso("X13")
@pytest.mark.requisito("RF1,RNF4")
def test_X13_mensajes_inmutables_y_sin_entrada():
    sh = Hospital(1,12,Parametros()).compartir()[0]
    assert set(vars(sh)) == {"sid","origen","destino","valor"}
    with pytest.raises(FrozenInstanceError):
        sh.valor = 1
    with pytest.raises(FrozenInstanceError):
        Parametros().p = 97


@pytest.mark.caso("X14")
@pytest.mark.requisito("RNF3")
def test_X14_servidor_espera_y_aborta_al_vencer_T():
    p,reloj = Parametros(),RelojManual()
    s = Servidor(1,p,reloj)
    s.recibir(Share(p.sid,1,1,5))
    with pytest.raises(Pendiente):
        s.agregar()
    reloj.avanzar(p.T)
    with pytest.raises(SesionAbortada):
        s.agregar()
    assert s.estado == Estado.ABORTADO


@pytest.mark.caso("X15")
@pytest.mark.requisito("RF3,RNF4")
def test_X15_cota_publica_no_asegura_verdad():
    p,a = Parametros(),Analista(Parametros())
    for j in (1,2,3):
        a.recibir(Parcial(p.sid,j,126))
    with pytest.raises(SesionAbortada, match="cota"):
        a.reconstruir()


@pytest.mark.caso("X16")
@pytest.mark.requisito("RF3,RNF1")
def test_X16_fuga_del_resultado():
    xs = [12,23,31]
    total = ejecutar(xs)[0].valor
    assert total-xs[0]-xs[1] == xs[2]
