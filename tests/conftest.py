"""Evidencia por prueba y certificados efímeros para el laboratorio TLS."""
import csv
import hashlib
import json
from pathlib import Path
import platform
import ssl
import subprocess
import sys
import pytest


def pytest_addoption(parser):
    parser.addoption("--evidencia", default=None, help="directorio de resultados JSON y CSV")


def pytest_configure(config):
    config.evidencias = []
    config.estadistica = {}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        caso = item.get_closest_marker("caso")
        req = item.get_closest_marker("requisito")
        item.config.evidencias.append({
            "caso": caso.args[0] if caso else "SIN_ID",
            "requisitos": req.args[0] if req else "SIN_REQ",
            "prueba": item.nodeid,
            "estado": report.outcome,
            "segundos": round(report.duration, 6),
        })


def pytest_sessionfinish(session, exitstatus):
    destino = session.config.getoption("--evidencia")
    if not destino:
        return
    ruta = Path(destino)
    ruta.mkdir(parents=True, exist_ok=True)
    raiz = Path(__file__).resolve().parents[1]
    fuentes = sorted([*raiz.glob("suma_segura/*.py"), *raiz.glob("tests/*.py"),
                      raiz / "demo.py", raiz / "requirements.txt", raiz / "pytest.ini"])
    resumen = {"python": sys.version, "plataforma": platform.platform(),
               "pytest": pytest.__version__, "openssl": ssl.OPENSSL_VERSION,
               "salida": int(exitstatus), "pruebas": session.config.evidencias,
               "uniformidad": session.config.estadistica,
               "sha256_fuentes": {str(p.relative_to(raiz)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in fuentes}}
    (ruta / "resultados.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    with (ruta / "tabla_pruebas.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["caso", "requisitos", "prueba", "estado", "segundos"])
        w.writeheader()
        w.writerows(session.config.evidencias)


@pytest.fixture(scope="session")
def certificados(tmp_path_factory):
    """OpenSSL CLI genera claves nuevas; no se distribuyen claves privadas."""
    base = tmp_path_factory.mktemp("tls")

    def ejecutar(*args):
        subprocess.run(["openssl", *map(str, args)], cwd=base, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)

    for ca in ("ca", "otra_ca"):
        ejecutar("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256",
                 "-days", "2", "-keyout", ca+".key", "-out", ca+".crt",
                 "-subj", "/CN="+ca, "-addext", "basicConstraints=critical,CA:TRUE")
    for nombre, cn, ca, servidor in (("servidor", "localhost", "ca", True),
                                      ("hospital", "H1", "ca", False),
                                      ("parcial", "S1", "ca", False),
                                      ("intruso", "H1", "otra_ca", False)):
        ejecutar("req", "-new", "-newkey", "rsa:2048", "-nodes", "-sha256",
                 "-keyout", nombre+".key", "-out", nombre+".csr", "-subj", "/CN="+cn)
        ext = base / (nombre+".ext")
        ext.write_text("basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\n"
                       + ("extendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost\n" if servidor
                          else "extendedKeyUsage=clientAuth\n"))
        ejecutar("x509", "-req", "-in", nombre+".csr", "-CA", ca+".crt", "-CAkey", ca+".key",
                 "-CAcreateserial", "-out", nombre+".crt", "-days", "2", "-sha256", "-extfile", ext)
    return base
