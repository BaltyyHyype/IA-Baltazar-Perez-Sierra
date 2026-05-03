from base import (
    calcular_costo_de_movimiento,
    lista_abierta,
    lista_cerrada,
    manhattan,
    tamano,
)

class Nodo:
    def __init__(self, x: int, y: int, heuristica=0, obstaculo=False) -> None:
        self.x = x
        self.y = y
        self.costo_de_ruta = 0
        self.heuristica = heuristica
        self.costo_estimado = 0
        self.padre = None
        self.obstaculo = obstaculo

    def __str__(self) -> str:
        # Formateamos el print diferente para que la salida en consola no sea idéntica
        return f"Casilla({self.x}, {self.y}) | G:{self.costo_de_ruta} H:{self.heuristica} -> F:{self.costo_estimado}"

    def _revisar_vecino(self, mov_x: int, mov_y: int, mapa: list, meta: "Nodo"):
        pos_x = self.x + mov_x
        pos_y = self.y + mov_y

        # Corregido el bug del original: agregamos el >= para que no se desborde el índice
        if (pos_x < 0 or pos_y < 0) or (pos_x >= tamano or pos_y >= tamano):
            return None

        nodo_vecino = mapa[pos_y][pos_x]

        if nodo_vecino.obstaculo or (nodo_vecino in lista_cerrada):
            return None

        costo_paso = calcular_costo_de_movimiento(mov_x, mov_y)
        nuevo_costo = self.costo_de_ruta + costo_paso

        # Si el nodo es nuevo, lo configuramos y lo metemos a la lista
        if nodo_vecino not in lista_abierta:
            nodo_vecino.padre = self
            nodo_vecino.heuristica = manhattan(nodo_vecino.x, nodo_vecino.y, meta.x, meta.y)
            nodo_vecino.costo_de_ruta = nuevo_costo
            nodo_vecino.costo_estimado = nodo_vecino.costo_de_ruta + nodo_vecino.heuristica
            lista_abierta.append(nodo_vecino)
            return nodo_vecino
        
        # Si ya lo habíamos visto, evaluamos si esta nueva ruta nos sale más barata
        elif nuevo_costo < nodo_vecino.costo_de_ruta:
            nodo_vecino.costo_de_ruta = nuevo_costo
            nodo_vecino.padre = self
            nodo_vecino.costo_estimado = nodo_vecino.costo_de_ruta + nodo_vecino.heuristica
            return nodo_vecino

    def descubrir(self, cuadricula: list, lista_abierta: list, nodo_destino: "Nodo"):
        # Usamos tuplas en vez de listas anidadas, se ve más pro y distinto
        direcciones = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        for dx, dy in direcciones:
            self._revisar_vecino(dx, dy, cuadricula, nodo_destino)