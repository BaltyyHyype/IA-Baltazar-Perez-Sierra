from base import lista_abierta, lista_cerrada, manhattan, tamano
from nodo import Nodo


def preparar_cuadricula(tam):
    # Genera la matriz limpia
    return [[Nodo(x, y) for x in range(tam)] for y in range(tam)]


def establecer_puntos(matriz, x_ini, y_ini, x_fin, y_fin):
    # Definimos la meta primero para poder calcular la heurística del inicio
    meta = Nodo(x_fin, y_fin)
    matriz[y_fin][x_fin] = meta
    
    # Definimos el punto de arranque
    arranque = Nodo(x_ini, y_ini, heuristica=manhattan(x_ini, y_ini, x_fin, y_fin))
    matriz[y_ini][x_ini] = arranque
    
    return arranque, meta


def cargar_obstaculos(matriz, lista_coordenadas):
    # Metemos todos los obstáculos de jalón iterando una lista
    for x, y in lista_coordenadas:
        matriz[y][x] = Nodo(x, y, obstaculo=True)


def ejecutar_busqueda():
    mapa = preparar_cuadricula(tamano)
    
    nodo_inicio, nodo_meta = establecer_puntos(mapa, 0, 0, 3, 0)
    
    # Pasamos las coordenadas de los muros en una sola lista, se ve más limpio
    muros = [(1, 0), (1, 1), (1, 3)]
    cargar_obstaculos(mapa, muros)

    lista_abierta.append(nodo_inicio)

    while lista_abierta:
        # En vez de ordenar la lista entera (que es más lento), sacamos directo el de menor costo
        nodo_actual = min(lista_abierta, key=lambda n: n.costo_estimado)
        lista_abierta.remove(nodo_actual)

        if nodo_actual == nodo_meta:
            print("--- Búsqueda Finalizada ---")
            print(f"Origen: {nodo_inicio}")
            print(f"Destino: {nodo_meta}")
            print("Ruta a seguir:")
            
            camino = []
            temporal = nodo_actual
            
            # Reconstruimos la ruta hacia atrás
            while temporal != (lista_cerrada[0] if lista_cerrada else None):
                camino.append(temporal)
                temporal = temporal.padre
                if temporal is None:
                    break
                    
            camino.append(nodo_inicio)
            camino.reverse()
            
            for paso in camino:
                print(paso)
            return  # Cortamos la ejecución aquí

        nodo_actual.descubrir(mapa, lista_abierta, nodo_meta)
        lista_cerrada.append(nodo_actual)


if __name__ == "__main__":
    ejecutar_busqueda()