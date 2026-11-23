from suma_segura import Parametros, ejecutar

if __name__ == "__main__":
    for caidos in ((), (2,)):
        salida, _, _ = ejecutar([12, 23, 31], Parametros(), caidos)
        print(f"S={salida.valor}; servidores={salida.servidores}; degradado={salida.degradado}")
