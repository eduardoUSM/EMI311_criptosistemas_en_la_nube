# EMI311 Entregable 4

Prototipo de suma segura entre tres hospitales. Continúa el Entregable 3 con
Shamir 2 de 3 y comprobación de colinealidad. El caso principal utiliza
n=3, m=3, M=40, p=127 y T=10 segundos de tiempo lógico.

## Qué incluye

- `suma_segura/`: parámetros y mensajes inmutables, Hospital, Servidor, Analista,
  simulación y laboratorio de transporte TLS.
- `tests/`: plan T1–T11 del Entregable 3 y casos X1–X17 adicionales.
- `resultados/`: salida original de pytest, tabla CSV, JUnit y JSON con entorno,
  estadístico de uniformidad y hashes SHA-256 del código probado.
- `Informe_EMI311_Entregable_4.pdf`: análisis de seguridad de seis páginas.
- `Informe_EMI311_Entregable_4.docx`: versión editable del mismo análisis.
- `GUIA_DE_REVISION.md`: cómo revisar los archivos y explicar el prototipo.

El protocolo se ejecuta con llamadas entre objetos de un único proceso. El
laboratorio TLS es una prueba real independiente sobre sockets locales; no
convierte la simulación en un servicio de red ni en un despliegue multi-nube.

## Requisitos

Python 3.10 o superior con soporte TLS 1.3; OpenSSL CLI 3.x en PATH para generar
certificados temporales. Dependencia de pruebas: pytest 9.0.2. La ejecución
original utilizó Python 3.12.14; el detalle del entorno está en resultados.json.

## Instalación y ejecución

Abrir una terminal **dentro de esta carpeta**, después de descomprimir:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python demo.py
python -m pytest -v --evidencia=resultados_nuevos --junitxml=resultados_nuevos/junit.xml > salida_nueva.txt 2>&1
```

En Windows, crear el entorno con `py -m venv .venv` y activarlo con
`.venv\Scripts\Activate.ps1` en PowerShell. Usar después `python` en los comandos.
OpenSSL debe estar instalado y accesible en esa terminal.

Para ver la salida en pantalla sin guardarla:

```bash
python -m pytest -v --evidencia=resultados_nuevos
```

La demostración devuelve:

```text
S=66; servidores=(1, 2, 3); degradado=False
S=66; servidores=(1, 3); degradado=True
```

No se requieren cuentas cloud, bases de datos ni datos clínicos. Las pruebas TLS
generan claves nuevas en la carpeta temporal de pytest; no hay claves privadas
en este archivo comprimido. No se omite T8 si falta OpenSSL: la prueba falla e
indica el requisito pendiente. No se necesitan permisos de administrador.

## Cómo interpretar los resultados

La ejecución original obtuvo **61 passed**, sin omisiones ni fallos. Ese número
cuenta casos parametrizados, no 61 propiedades independientes. T1 contiene
1.000 ejecuciones dentro de una prueba; T9 contiene 10.000 comparticiones.
Los IDs se conservan según el E3 del estudiante: T8 es autenticación TLS, T10
es caída de S2 y T11 es detección. La numeración del apunte de referencia difiere.

Cada prueba tiene marcadores `caso` y `requisito`. `tabla_pruebas.csv` contiene
una fila por caso ejecutado. `resultados.json` agrega el entorno, los hashes del
código y las frecuencias de T9. Las pruebas de coaliciones y manipulación que
aprueban muestran límites conocidos, no garantías contra esos ataques.

La T3 del E3 decía que debían excluirse pendientes o shares cero. Aquí se corrige:
a se toma uniformemente de 0 a p-1, incluido cero; un share cero es válido.

T9 usa x=15, p=127 y N=10.000, como el plan propio. Con 10 intervalos definidos
por `b = 10*s//127`, los valores esperados consideran exactamente cuántos residuos
caen en cada intervalo. El valor original fue chi²=23,56601667, inferior a 27,88
(9 grados de libertad, alfa=0,001, criterio del material). La aleatoriedad
criptográfica y los certificados cambian en cada ejecución. Puede haber un falso
rechazo estadístico, aproximadamente una de cada mil ejecuciones bajo la
aproximación chi². Conservar el resultado e investigar; no repetir para elegir
una salida favorable. Aprobar esta prueba no demuestra impredecibilidad.

## Diseño y alcance

1. Hospital valida x entero en [0,M]. Usa exclusivamente `secrets.randbelow`
   para los secretos. `random.Random` aparece solo en T1 para los vectores de
   entrada reproducibles; nunca para generar shares.
2. Por defecto, f_i(t)=x_i+a_i*t mod p; el Hospital entrega un Share a cada
   Servidor. Share no contiene un campo x. Puede coincidir numéricamente con x
   por azar, sin implicar que se transmita x como dato de entrada.
3. Cada Servidor valida sid, origen, destino y residuo; conserva el primer
   aporte válido por hospital y emite un único Parcial.
4. Analista espera los tres parciales o el vencimiento T. Con tres comprueba
   colinealidad; con dos interpola y devuelve `degradado=True`; con menos aborta.
5. `RelojManual` permite probar plazos sin esperas reales. Los métodos devuelven
   `Pendiente` si aún falta información y el plazo sigue abierto. Una aplicación
   de red tendría que invocarlos desde un bucle de eventos con reloj real.
6. `esquema="aditivo"` mantiene el esquema base como comparación y permite
   pruebas con varios n,m. En él p puede ser compuesto. La extensión elegida
   exige m=3 y p primo; variar m no generaliza automáticamente su detector.
7. El módulo TLS fija TLS 1.3, valida la CA y el nombre del servidor y requiere
   certificado cliente. El CN del cliente debe coincidir con H_i o S_j según el
   origen declarado. Es una política de laboratorio con CA controlada, no una
   infraestructura de certificados para hospitales reales. Después del canal,
   el receptor de protocolo debe seguir validando sesión, rol, destino y rango.

## Límites que no deben ocultarse

- Shamir 2/3 protege frente a un servidor; dos pueden recuperar cada x_i.
- Con tres parciales se detecta un único parcial alterado. No se identifica ni
  corrige al responsable. Con dos no hay redundancia para esa comprobación.
- Dos alteraciones coordinadas pueden pasar la colinealidad y cambiar el total.
- El total publicado permite inferencias. Dos hospitales pueden calcular la
  entrada del tercero con sus cifras y S.
- El rango no prueba la veracidad de una cifra clínica.
- En un solo proceso, las vistas no tienen aislamiento físico. Se guardan solo
  para inspección con datos sintéticos. Los eventos no registran valores.
- No se garantiza borrado de memoria Python, resistencia a canales laterales,
  disponibilidad real, gestión de claves, revocación ni recuperación tras reinicio.
- El sid de ejemplo es fijo para la demostración. En producción debe ser único,
  acordado y protegido contra reutilización, con estado persistente de sesiones.

## Fuentes del trabajo

Material del docente: presentación de Clase 4, láminas 29–31; Capítulo 4,
secciones 4.1–4.8; infografía de Clases 4 y 5. Diseño de partida: informe propio
Entregable 3, secciones 3 y 4, y modelos del Entregable 2. Se usa una implementación
propia organizada a partir de esos modelos; no se incluye el código completo del
prototipo de referencia como si fuera trabajo propio.
