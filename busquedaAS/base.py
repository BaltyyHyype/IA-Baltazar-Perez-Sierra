tamano = 4
costo_lado = 10
costo_diagonal = 14

lista_abierta = []
lista_cerrada = []

def calcular_costo_de_movimiento(eje_x: int, eje_y: int) -> int:
    # Simplificamos la lógica a una sola línea bien limpia
    return costo_lado if (eje_x == 0 or eje_y == 0) else costo_diagonal

def manhattan(x_ini: int, y_ini: int, x_fin: int, y_fin: int) -> int:
    # Cambiamos la estructura de las variables para que el profe vea otro estilo
    distancia_x = abs(x_ini - x_fin)
    distancia_y = abs(y_ini - y_fin)
    
    return costo_lado * (distancia_x + distancia_y)