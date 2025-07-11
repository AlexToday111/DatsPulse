# Константы игры
ANT_TYPES = {
    0: "worker",    # Рабочий
    1: "warrior",   # Боец
    2: "scout"      # Разведчик
}

RESOURCE_TYPES = {
    1: "apple",     # Яблоко
    2: "bread",     # Хлеб
    3: "nectar"     # Нектар
}

HEX_TYPES = {
    1: "home",      # Муравейник
    2: "empty",     # Пустой
    3: "dirt",      # Грязь
    4: "acid",      # Кислота
    5: "stones"     # Камни
}

# Стоимость перемещения
MOVE_COSTS = {
    1: 1,   # home
    2: 1,   # empty
    3: 2,   # dirt
    4: 1,   # acid
    5: float('inf')  # stones (непроходимо)
}

# Приоритет ресурсов (чем выше, тем ценнее)
RESOURCE_PRIORITY = {
    1: 1.0,  # apple
    2: 1.5,  # bread
    3: 3.0   # nectar
}

# API конфигурация
API_URL = "https://games.datsteam.dev/api/datspulse"
API_RATE_LIMIT = 3  # запросов в секунду
