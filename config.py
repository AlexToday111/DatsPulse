# Конфигурация API
API_URL = "https://games-test.datsteam.dev"  # Тестовый сервер
# API_URL = "https://games.datsteam.dev"  # Боевой сервер
API_TOKEN = "YOUR_API_TOKEN_HERE"

# Константы типов
ANT_TYPES = {
    0: "worker",
    1: "warrior",
    2: "scout"
}

RESOURCE_TYPES = {
    1: "apple",
    2: "bread",
    3: "nectar"
}

HEX_TYPES = {
    1: "home",
    2: "empty",
    3: "dirt",
    4: "acid",
    5: "stones"
}

# Стоимость перемещения по типам гексов
MOVE_COSTS = {
    1: 1,   # home
    2: 1,   # empty
    3: 2,   # dirt
    4: 1,   # acid
    5: float('inf')  # stones (непроходимо)
}
