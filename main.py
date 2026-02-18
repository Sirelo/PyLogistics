import arcade
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

SCREEN_WIDTH = 1008
SCREEN_HEIGHT = 800
SCREEN_TITLE = "Industrial Complex — Factory Management Simulator"

GRID_SIZE = 48
ROWS = (SCREEN_HEIGHT - 180) // GRID_SIZE
COLS = SCREEN_WIDTH // GRID_SIZE


class ResourceType(Enum):
    ORE = "ore"
    COAL = "coal"
    IRON = "iron"
    STEEL = "steel"
    COPPER = "copper"
    CIRCUIT = "circuit"
    ENGINE = "engine"
    ROBOT = "robot"
    ELECTRONICS = "electronics"
    CAR = "car"
    COMPUTER = "computer"


@dataclass
class Resource:
    name: str
    value: int
    color: Tuple[int, int, int]
    icon: str


RESOURCES = {
    ResourceType.ORE: Resource("Руда", 50, (139, 69, 19), "●"),
    ResourceType.COAL: Resource("Уголь", 30, (34, 34, 34), "◆"),
    ResourceType.IRON: Resource("Железо", 100, (169, 169, 169), "■"),
    ResourceType.STEEL: Resource("Сталь", 250, (192, 192, 192), "▲"),
    ResourceType.COPPER: Resource("Медь", 150, (184, 115, 51), "★"),
    ResourceType.CIRCUIT: Resource("Микросхема", 500, (0, 255, 127), "⊕"),
    ResourceType.ENGINE: Resource("Двигатель", 800, (255, 69, 0), "◈"),
    ResourceType.ROBOT: Resource("Робот", 1500, (0, 191, 255), "⚙"),
    ResourceType.ELECTRONICS: Resource("Электроника", 1200, (147, 112, 219), "☢"),
    ResourceType.CAR: Resource("Автомобиль", 5000, (220, 20, 60), "🚗"),
    ResourceType.COMPUTER: Resource("Компьютер", 3000, (30, 144, 255), "💻"),
}


# =========================================================
#                   ЭКОНОМИКА
# =========================================================
class Economy:
    def __init__(self, start_money=15000):
        self.balance = start_money
        self.daily_profit = 0
        self.total_production = 0
        self.total_sales = 0
        self.production_stats = {resource_type: 0 for resource_type in ResourceType}
        self.sales_stats = {resource_type: 0 for resource_type in ResourceType}

    def spend(self, amount: int) -> bool:
        if self.balance >= amount:
            self.balance -= amount
            return True
        return False

    def earn(self, amount: int, resource_type: ResourceType):
        self.balance += amount
        self.total_sales += amount
        self.sales_stats[resource_type] += amount
        self.daily_profit = self.total_sales - int(self.total_production * 0.7)

    def track_production(self, resource_type: ResourceType, cost: int):
        self.total_production += cost
        self.production_stats[resource_type] += cost


economy = Economy()


class Direction(Enum):
    UP = (1, 0)
    DOWN = (-1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)


# =========================================================
#                БАЗОВЫЙ КЛАСС МОДУЛЯ
# =========================================================
class Building:
    cost = 0
    upkeep = 0
    cycle_time = 1.0
    input_types = []
    output_type = None
    production_cost = 0

    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col
        self.direction = Direction.RIGHT
        self.item = None
        self.timer = 0.0
        self.progress = 0.0
        self.efficiency = 1.0

    def get_output_coords(self) -> Tuple[int, int]:
        dr, dc = self.direction.value
        return self.row + dr, self.col + dc

    def get_input_coords(self) -> List[Tuple[int, int]]:
        all_dirs = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        return [(self.row + d.value[0], self.col + d.value[1])
                for d in all_dirs if d != self.direction]

    def can_accept(self, item_type: ResourceType, from_coords: Tuple[int, int]) -> bool:
        # Конвейеры принимают всё, заводы — только нужное
        if isinstance(self, Conveyor):
            return self.item is None
        is_input_side = from_coords in self.get_input_coords()
        return self.item is None and item_type in self.input_types and is_input_side

    def accept_item(self, item_type: ResourceType, from_coords: Tuple[int, int]) -> bool:
        if self.can_accept(item_type, from_coords):
            self.item = item_type
            return True
        return False

    def do_cycle(self, delta_time: float) -> bool:
        self.timer += delta_time
        if self.timer >= self.cycle_time:
            self.timer = 0.0
            return True
        return False

    def charge_upkeep(self):
        economy.spend(self.upkeep)

    def process(self, grid, delta_time: float):
        """Пытается передать предмет следующему зданию"""
        if self.item is not None:
            out_r, out_c = self.get_output_coords()
            if 0 <= out_r < ROWS and 0 <= out_c < COLS:
                target = grid[out_r][out_c]
                if target and target.accept_item(self.item, (self.row, self.col)):
                    self.item = None


# =========================================================
#                   ПРОМЫШЛЕННЫЕ МОДУЛИ
# =========================================================


class Mine(Building):
    cost = 300
    upkeep = 5
    cycle_time = 3.0
    output_type = ResourceType.ORE

    def process(self, grid, delta_time):
        if self.do_cycle(delta_time):
            self.charge_upkeep()
            if self.item is None and economy.spend(20):
                self.item = ResourceType.ORE
                economy.track_production(ResourceType.ORE, 20)
        super().process(grid, delta_time)  # Выталкиваем руду


class CoalMine(Building):
    cost = 350
    upkeep = 7
    cycle_time = 2.5
    output_type = ResourceType.COAL

    def process(self, grid, delta_time: float):
        if self.do_cycle(delta_time):
            self.charge_upkeep()
            if self.item is None and economy.spend(15):
                self.item = ResourceType.COAL
                economy.track_production(ResourceType.COAL, 15)
        super().process(grid, delta_time)


class Smelter(Building):
    cost = 800
    upkeep = 15
    cycle_time = 4.0
    input_types = [ResourceType.ORE, ResourceType.COAL]
    output_type = ResourceType.IRON
    production_cost = 50

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.input_a = None
        self.input_b = None
        self.heat = 0.0
        self.is_active = False

    def can_accept(self, item_type: ResourceType, from_coords: Tuple[int, int]) -> bool:
        is_input_side = from_coords in self.get_input_coords()
        has_space = (self.input_a is None or self.input_b is None)
        return is_input_side and has_space and item_type in self.input_types

    def accept_item(self, item_type: ResourceType, from_coords: Tuple[int, int]) -> bool:
        if self.can_accept(item_type, from_coords):
            if self.input_a is None:
                self.input_a = item_type
            else:
                self.input_b = item_type
            return True
        return False

    def process(self, grid, delta_time: float):
        if self.input_a and self.input_b and not self.is_active and self.item is None:
            self.is_active = True
            self.progress = 0.0

        if self.is_active:
            self.progress += delta_time
            if self.progress >= self.cycle_time:
                self.item = ResourceType.IRON
                self.input_a = None
                self.input_b = None
                self.is_active = False
                self.progress = 0.0
                economy.track_production(ResourceType.IRON, self.production_cost)
                self.charge_upkeep()

        super().process(grid, delta_time)  # Выталкиваем металл


class SteelMill(Building):
    cost = 1200
    upkeep = 25
    cycle_time = 5.0
    input_types = [ResourceType.IRON, ResourceType.COAL]
    output_type = ResourceType.STEEL
    production_cost = 100

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.input_a = None
        self.input_b = None

    def can_accept(self, item_type: ResourceType, from_coords: Tuple[int, int]) -> bool:
        is_input_side = from_coords in self.get_input_coords()
        has_space = (self.input_a is None or self.input_b is None)
        return is_input_side and has_space and item_type in self.input_types

    def accept_item(self, item_type: ResourceType, from_coords: Tuple[int, int]) -> bool:
        if self.can_accept(item_type, from_coords):
            if self.input_a is None:
                self.input_a = item_type
            else:
                self.input_b = item_type
            return True
        return False

    def process(self, grid, delta_time: float):
        # Если есть ингредиенты и место для выхода — запускаем цикл
        if self.input_a and self.input_b and self.item is None:
            if self.do_cycle(delta_time):
                self.charge_upkeep()
                if economy.spend(self.production_cost):
                    self.item = ResourceType.STEEL
                    self.input_a = None
                    self.input_b = None
                    economy.track_production(ResourceType.STEEL, self.production_cost)

        # ВАЖНО: передаем результат дальше
        super().process(grid, delta_time)


class ElectronicsFactory(Building):
    cost = 1500
    upkeep = 30
    cycle_time = 4.0
    input_types = [ResourceType.COPPER, ResourceType.CIRCUIT]
    output_type = ResourceType.ELECTRONICS
    production_cost = 300

    def __init__(self, row: int, col: int):
        super().__init__(row, col)

    def process(self, grid, delta_time: float):
        if self.do_cycle(delta_time) and self.item is None:
            self.charge_upkeep()
            if economy.spend(self.production_cost):
                self.item = ResourceType.ELECTRONICS
                economy.track_production(ResourceType.ELECTRONICS, self.production_cost)

        # ВАЖНО: Этот вызов передает созданный предмет на конвейер или в маркет
        super().process(grid, delta_time)


class RobotFactory(Building):
    cost = 3000
    upkeep = 50
    cycle_time = 8.0
    input_types = [ResourceType.STEEL, ResourceType.ELECTRONICS, ResourceType.CIRCUIT]
    output_type = ResourceType.ROBOT
    production_cost = 800

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.arm_rotation = 0.0
        self.is_assembling = False

    def process(self, grid, delta_time: float):
        if self.do_cycle(delta_time) and self.item is None:
            self.charge_upkeep()
            if economy.spend(self.production_cost):
                self.item = ResourceType.ROBOT
                economy.track_production(ResourceType.ROBOT, self.production_cost)
        if self.is_assembling and self.progress >= 1.0:
            self.is_assembling = False


class ComputerFactory(Building):
    cost = 2500
    upkeep = 45
    cycle_time = 7.0
    input_types = [ResourceType.ELECTRONICS, ResourceType.CIRCUIT]
    output_type = ResourceType.COMPUTER
    production_cost = 600

    def __init__(self, row: int, col: int):
        super().__init__(row, col)

    def process(self, grid, delta_time: float):
        if self.do_cycle(delta_time) and self.item is None:
            self.charge_upkeep()
            if economy.spend(self.production_cost):
                self.item = ResourceType.COMPUTER
                economy.track_production(ResourceType.COMPUTER, self.production_cost)

        # ВАЖНО: Этот вызов передает созданный компьютер дальше
        super().process(grid, delta_time)


class Conveyor(Building):
    cost = 100
    upkeep = 1
    cycle_time = 0.5

    def process(self, grid, delta_time: float):
        # Конвейеру достаточно просто вызывать базовый процесс передачи
        super().process(grid, delta_time)


class Warehouse(Building):
    cost = 500
    upkeep = 10
    capacity = 10

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.storage = []
        self.stored_types = {rt: 0 for rt in ResourceType}

    def can_accept(self, item_type: ResourceType, from_coords: Tuple[int, int]) -> bool:
        # Проверяем, что предмет заходит с одной из 3 сторон входа
        is_input_side = from_coords in self.get_input_coords()
        return is_input_side and len(self.storage) < self.capacity

    def accept_item(self, item_type: ResourceType, from_coords: Tuple[int, int]) -> bool:
        if self.can_accept(item_type, from_coords):
            self.storage.append(item_type)
            self.stored_types[item_type] += 1
            return True
        return False

    def can_give_item(self) -> bool:
        return len(self.storage) > 0

    def process(self, grid, delta_time: float):
        if self.do_cycle(delta_time) and self.item is None and self.storage:
            self.item = self.storage.pop(0)
            self.stored_types[self.item] -= 1


class Market(Building):
    cost = 400
    upkeep = 8
    cycle_time = 2.0

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.sell_prices = {
            ResourceType.ORE: 80, ResourceType.COAL: 50,
            ResourceType.IRON: 150, ResourceType.STEEL: 350,
            ResourceType.COPPER: 200, ResourceType.CIRCUIT: 600,
            ResourceType.ELECTRONICS: 1500, ResourceType.ENGINE: 1000,
            ResourceType.ROBOT: 2000, ResourceType.CAR: 6000,
            ResourceType.COMPUTER: 4000,
        }

    # Исправляем сигнатуру: добавляем from_coords
    def can_accept(self, item_type: ResourceType, from_coords: Tuple[int, int]) -> bool:
        # Маркет принимает любой ресурс из списка цен, если в нем сейчас пусто
        return self.item is None and item_type in self.sell_prices

    # Также исправляем accept_item, чтобы соответствовать базе
    def accept_item(self, item_type: ResourceType, from_coords: Tuple[int, int]) -> bool:
        if self.can_accept(item_type, from_coords):
            self.item = item_type
            return True
        return False

    def process(self, grid, delta_time: float):
        # Если в Маркете есть предмет — продаем его немедленно
        if self.item:
            price = self.sell_prices.get(self.item, 0)
            economy.earn(price, self.item)
            self.item = None  # ОЧЕНЬ ВАЖНО: очищаем слот, чтобы Маркет мог принять следующий предмет


# =========================================================
#                     ИГРА
# =========================================================
class MyGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        self.grid: List[List[Optional[Building]]] = [
            [None for _ in range(COLS)] for _ in range(ROWS)
        ]
        self.dir_names = {
            Direction.UP: "ВВЕРХ",
            Direction.DOWN: "ВНИЗ",
            Direction.LEFT: "ВЛЕВО",
            Direction.RIGHT: "ВПРАВО"
        }
        self.simulation_running = False
        self.current_rotation = Direction.RIGHT  # Добавьте эту строку!
        self.build_mode = None
        self.selected_building = None
        self.show_stats = False
        self.time_scale = 1.0
        self.day_timer = 0.0
        self.day_length = 60.0

        # Координаты мыши
        self.mouse_x: int = 0
        self.mouse_y: int = 0

        # Палитра цветов для UI
        self.ui_colors = {
            'bg_dark': (40, 44, 52),
            'bg_medium': (58, 63, 74),
            'bg_light': (78, 84, 96),
            'primary': (97, 175, 239),
            'secondary': (198, 120, 221),
            'success': (152, 195, 121),
            'warning': (229, 192, 123),
            'danger': (224, 108, 117),
            'text': (220, 223, 228),
            'text_dim': (171, 178, 191),
        }

        # Список доступных построек для панели
        self.available_buildings = [
            (1, "Шахта (руда)", Mine, 300),
            (2, "Угольная шахта", CoalMine, 350),
            (3, "Плавильня", Smelter, 800),
            (4, "Сталелитейный завод", SteelMill, 1200),
            (5, "Конвейер", Conveyor, 100),
            (6, "Электронный завод", ElectronicsFactory, 1500),
            (7, "Компьютерный завод", ComputerFactory, 2500),
            (8, "Склад", Warehouse, 500),
            ('M', "Рынок", Market, 400),
        ]

        # Инициализация Batch для оптимизации текста
        self.text_batch = arcade.pyglet.graphics.Batch()

        # Статический текст (заголовок и управление)
        self.ui_labels = []

        # Заголовок
        self.title_label = arcade.Text(
            "🏭 ПРОМЫШЛЕННЫЙ КОМПЛЕКС",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 35,
            self.ui_colors['primary'], 22, bold=True, anchor_x="center",
            batch=self.text_batch
        )

        # Управление
        controls_text = [
            "⚙️ УПРАВЛЕНИЕ:",
            "1-9,0,M - Выбор постройки",
            "ЛКМ - Построить | ПКМ - Удалить",
            "S - СТАРТ / ПАУЗА",
            "R - Сброс | ESC - Отмена выбора"
        ]
        for i, text in enumerate(controls_text):
            label = arcade.Text(
                text, 20, SCREEN_HEIGHT - 80 - i * 20,
                self.ui_colors['text_dim'], 12,
                batch=self.text_batch
            )
            self.ui_labels.append(label)

        # Динамические лейблы (создаем один раз, обновляем текст в on_update)
        self.balance_label = arcade.Text("", 20, 140, self.ui_colors['success'], 20, bold=True, batch=self.text_batch)
        self.profit_label = arcade.Text("", 320, 140, self.ui_colors['success'], 18, batch=self.text_batch)
        self.status_indicator_label = arcade.Text("", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 90, (255, 255, 255), 14,
                                                  bold=True, anchor_x="center", batch=self.text_batch)

    # ---------------------------------------
    # РИСОВАНИЕ UI
    # ---------------------------------------
    def draw_ui_panel(self):
        """Рисуем панель UI внизу экрана"""
        panel_height = 180
        panel_y = 0

        # Фон панели
        arcade.draw_lbwh_rectangle_filled(0, panel_y, SCREEN_WIDTH, panel_height, self.ui_colors['bg_dark'])

        # Верхняя граница панели
        arcade.draw_line(0, panel_y + panel_height, SCREEN_WIDTH, panel_y + panel_height,
                         self.ui_colors['primary'], 2)

        # Блок информации
        info_x = 20
        info_y = panel_y + panel_height - 40

        # Баланс
        balance_color = self.ui_colors['success'] if economy.balance >= 0 else self.ui_colors['danger']
        arcade.draw_text(f"💰 БАЛАНС: ${economy.balance:,}",
                         info_x, info_y, balance_color, 20, bold=True)

        # Дневная прибыль
        profit_color = self.ui_colors['success'] if economy.daily_profit >= 0 else self.ui_colors['danger']
        arcade.draw_text(f"📈 ДНЕВНАЯ ПРИБЫЛЬ: ${economy.daily_profit:+,}",
                         info_x + 300, info_y, profit_color, 18)

        # Статистика производства
        arcade.draw_text(f"⚙️ ПРОИЗВЕДЕНО: ${economy.total_production:,}",
                         info_x, info_y - 30, self.ui_colors['text'], 16)
        arcade.draw_text(f"📦 ПРОДАНО: ${economy.total_sales:,}",
                         info_x + 300, info_y - 30, self.ui_colors['text'], 16)

        # Панель построек
        building_panel_y = panel_y + 20
        building_size = 60
        building_spacing = 70
        start_x = 20

        for i, (hotkey, name, building_class, cost) in enumerate(self.available_buildings):
            x = start_x + i * building_spacing
            if x + building_size > SCREEN_WIDTH - 100:
                break

            # Фон кнопки
            button_color = self.ui_colors['primary'] if self.build_mode == hotkey else self.ui_colors['bg_medium']
            arcade.draw_lbwh_rectangle_filled(x, building_panel_y, building_size, building_size, button_color)

            # Обводка кнопки
            border_color = self.ui_colors['secondary'] if self.build_mode == hotkey else self.ui_colors['bg_light']
            arcade.draw_lbwh_rectangle_outline(x, building_panel_y, building_size, building_size, border_color, 2)

            # Иконка и текст
            arcade.draw_text(str(hotkey), x + building_size // 2 - 5, building_panel_y + 45,
                             self.ui_colors['text'], 14, bold=True)
            arcade.draw_text(f"${cost}", x + building_size // 2 - 15, building_panel_y + 15,
                             self.ui_colors['warning'], 12)

    def draw_tooltip(self, x: int, y: int, text: str):
        """Рисуем всплывающую подсказку"""
        lines = text.split('\n')
        max_width = max(len(line) for line in lines) * 7
        height = len(lines) * 20 + 10

        # Фон подсказки
        arcade.draw_lbwh_rectangle_filled(x + 10, y + 10, max_width, height, self.ui_colors['bg_dark'])
        arcade.draw_lbwh_rectangle_outline(x + 10, y + 10, max_width, height, self.ui_colors['primary'], 1)

        # Текст подсказки
        for i, line in enumerate(lines):
            arcade.draw_text(line, x + 15, y + height - 20 - i * 20, self.ui_colors['text'], 12)

    def draw_building_info(self, building):
        """Рисуем информацию о выбранном здании"""
        info_x = SCREEN_WIDTH - 250
        info_y = 140

        # Фон блока информации
        arcade.draw_lbwh_rectangle_filled(info_x, info_y, 230, 200, self.ui_colors['bg_medium'])
        arcade.draw_lbwh_rectangle_outline(info_x, info_y, 230, 200, self.ui_colors['primary'], 2)

        # Заголовок
        building_name = building.__class__.__name__
        arcade.draw_text("🏭 " + building_name, info_x + 10, info_y + 170,
                         self.ui_colors['text'], 16, bold=True)

        # Координаты
        arcade.draw_text(f"📍 Позиция: ({building.col}, {building.row})",
                         info_x + 10, info_y + 140, self.ui_colors['text_dim'], 12)

        # Состояние
        status = "⚡ Активен" if building.item else "⏸️ Ожидание"
        arcade.draw_text(f"📊 Статус: {status}",
                         info_x + 10, info_y + 115, self.ui_colors['text'], 12)

        # Прогресс
        if hasattr(building, 'progress'):
            progress_width = 200
            progress = building.progress / building.cycle_time if building.cycle_time > 0 else 0
            arcade.draw_lbwh_rectangle_filled(info_x + 15, info_y + 85, progress_width, 8, self.ui_colors['bg_light'])
            arcade.draw_lbwh_rectangle_filled(info_x + 15, info_y + 85, int(progress_width * progress), 8,
                                              self.ui_colors['success'])
            arcade.draw_text(f"⏳ Прогресс: {progress * 100:.0f}%",
                             info_x + 10, info_y + 100, self.ui_colors['text'], 11)

    def draw_resource_legend(self):
        """Рисуем легенду ресурсов"""
        legend_x = SCREEN_WIDTH - 250
        legend_y = SCREEN_HEIGHT - 30

        arcade.draw_text("📦 РЕСУРСЫ:", legend_x, legend_y, self.ui_colors['text'], 14, bold=True)

        y_offset = legend_y - 25
        resources_to_show = list(RESOURCES.items())[:6]  # Показываем первые 6 ресурсов

        for i, (resource_type, resource) in enumerate(resources_to_show):
            if i >= 6:  # Показываем только 6 в одном столбце
                break
            arcade.draw_text(resource.icon, legend_x, y_offset - i * 20, resource.color, 14)
            arcade.draw_text(resource.name, legend_x + 20, y_offset - i * 20,
                             self.ui_colors['text_dim'], 12)

    def draw_grid_background(self):
        """Рисуем фон сетки с паттерном"""
        for r in range(ROWS):
            for c in range(COLS):
                x = c * GRID_SIZE
                y = r * GRID_SIZE

                # Чередующийся фон для сетки
                if (r + c) % 2 == 0:
                    arcade.draw_lbwh_rectangle_filled(x, y, GRID_SIZE, GRID_SIZE, self.ui_colors['bg_dark'])
                else:
                    arcade.draw_lbwh_rectangle_filled(x, y, GRID_SIZE, GRID_SIZE, self.ui_colors['bg_medium'])

                # Точки на пересечениях для красоты
                arcade.draw_circle_filled(x, y, 1, self.ui_colors['text_dim'])

    def draw_building(self, building, x: int, y: int):
        """Рисует здание с круглым индикатором занятости без анимаций ресурсов"""
        # 1. Определяем базовый цвет здания
        if isinstance(building, Mine):
            color = (139, 69, 19)
        elif isinstance(building, CoalMine):
            color = (34, 34, 34)
        elif isinstance(building, Smelter):
            color = (255, 140, 0)
        elif isinstance(building, SteelMill):
            color = (192, 192, 192)
        elif isinstance(building, RobotFactory):
            color = (0, 191, 255)
        elif isinstance(building, Warehouse):
            color = (160, 82, 45)
        elif isinstance(building, Market):
            color = (152, 195, 121)
        elif isinstance(building, Conveyor):
            color = (70, 70, 70)
        else:
            color = (100, 100, 100)

        # 2. Рисуем корпус здания
        arcade.draw_lbwh_rectangle_filled(x, y, GRID_SIZE, GRID_SIZE, color)
        arcade.draw_lbwh_rectangle_outline(x, y, GRID_SIZE, GRID_SIZE, (255, 255, 255, 100), 2)

        # 3. Рисуем КРУГ индикатора занятости в центре
        # Зеленый - свободно, Красный - занято
        indicator_color = self.ui_colors['danger'] if building.item else self.ui_colors['success']

        center_x = x + GRID_SIZE // 2
        center_y = y + GRID_SIZE // 2

        # Рисуем подложку для круга (обводку)
        arcade.draw_circle_filled(center_x, center_y, 10, (0, 0, 0, 150))
        # Рисуем сам индикатор
        arcade.draw_circle_filled(center_x, center_y, 8, indicator_color)

        # Отрисовка индикатора ВЫХОДА
        cx, cy = x + GRID_SIZE // 2, y + GRID_SIZE // 2
        dr, dc = building.direction.value
        # Смещаем желтую точку в сторону, куда здание смотрит (выход)
        indicator_x = cx + dc * (GRID_SIZE // 2.5)
        indicator_y = cy + dr * (GRID_SIZE // 2.5)

        arcade.draw_circle_filled(indicator_x, indicator_y, 5, arcade.color.YELLOW)

    # ---------------------------------------
    # ОСНОВНОЕ РИСОВАНИЕ
    # ---------------------------------------
    def on_draw(self):
        self.clear()

        # 1. Фон и сетка
        arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (25, 25, 35))
        self.draw_grid_background()

        # 2. Линии сетки (рисуем один раз)
        for r in range(ROWS + 1):
            arcade.draw_line(0, r * GRID_SIZE, SCREEN_WIDTH, r * GRID_SIZE, self.ui_colors['bg_light'], 1)
        for c in range(COLS + 1):
            arcade.draw_line(c * GRID_SIZE, 0, c * GRID_SIZE, ROWS * GRID_SIZE, self.ui_colors['bg_light'], 1)

        # 3. Здания (только отрисовка, без логики текста!)
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                if cell:
                    self.draw_building(cell, c * GRID_SIZE, r * GRID_SIZE)

        # 4. ВАЖНО: Подсказка при наведении (рисуется ОДИН РАЗ поверх всего)
        mouse_grid_row = self.mouse_y // GRID_SIZE
        mouse_grid_col = self.mouse_x // GRID_SIZE
        if 0 <= mouse_grid_row < ROWS and 0 <= mouse_grid_col < COLS:
            b = self.grid[mouse_grid_row][mouse_grid_col]
            if b:
                status = "ЗАНЯТО" if b.item else "СВОБОДНО"
                item_name = RESOURCES[b.item].name if b.item else "Пусто"
                info_text = f"Объект: {b.__class__.__name__}\nСтатус: {status}\nСодержимое: {item_name}"
                self.draw_tooltip(self.mouse_x, self.mouse_y, info_text)

        # 5. UI элементы
        self.draw_ui_panel()
        self.draw_resource_legend()

        # --- ИНДИКАТОР СИМУЛЯЦИИ ВВЕРХУ (ИСПРАВЛЕНО) ---
        status_text = "СИМУЛЯЦИЯ: ЗАПУЩЕНА" if self.simulation_running else "СИМУЛЯЦИЯ: ПАУЗА"
        status_color = self.ui_colors['success'] if self.simulation_running else self.ui_colors['danger']

        box_width = 250
        box_height = 35
        center_x = SCREEN_WIDTH // 2
        top_y = SCREEN_HEIGHT - 65  # Верхняя точка
        bottom_y = top_y - box_height  # Нижняя точка (теперь точно меньше top_y)

        # Теперь bottom (703 - 35 = 668) меньше top (703)
        arcade.draw_lrbt_rectangle_filled(
            left=center_x - box_width // 2,
            right=center_x + box_width // 2,
            bottom=bottom_y,
            top=top_y,
            color=(0, 0, 0, 200)
        )

        arcade.draw_text(status_text, center_x, bottom_y + 10,
                         status_color, 14, bold=True, anchor_x="center")
        # ----------------------------------

        # Заголовок (чуть выше индикатора)
        arcade.draw_text("🏭 ПРОМЫШЛЕННЫЙ КОМПЛЕКС", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 35,
                         self.ui_colors['primary'], 22, bold=True, anchor_x="center")

        rotation_text = f"🔄 ПОВОРОТ ВЫХОДА: {self.dir_names[self.current_rotation]}"
        arcade.draw_text(rotation_text, 250, SCREEN_HEIGHT - 180,
                         self.ui_colors['warning'], 14, bold=True)

        # Также можно добавить подсказку про TAB в список управления
        # обновите ваш список controls_text:
        controls_text = [
            "⚙️ УПРАВЛЕНИЕ:",
            "1-9,0,M - Выбор постройки",
            "TAB - Повернуть здание (выход)",  # Новая строка
            "ЛКМ - Построить | ПКМ - Удалить",
            "S - СТАРТ / ПАУЗА",
            "R - Сброс | ESC - Отмена выбора"
        ]

        for i, text in enumerate(controls_text):
            arcade.draw_text(text, 20, SCREEN_HEIGHT - 80 - i * 20,
                             self.ui_colors['text_dim'], 12)

    # ---------------------------------------
    # ЛОГИКА
    # ---------------------------------------
    def on_update(self, delta_time: float):
        if not self.simulation_running:
            return

        self.day_timer += delta_time * self.time_scale
        if self.day_timer >= self.day_length:
            self.day_timer = 0
            economy.daily_profit = economy.total_sales - int(economy.total_production * 0.7)

        # Передаем delta_time в каждое здание
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                if cell:
                    cell.process(self.grid, delta_time)

    # ---------------------------------------
    # МЫШЬ
    # ---------------------------------------
    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        # Преобразуем координаты мыши в целые числа
        self.mouse_x = int(x)
        self.mouse_y = int(y)

        # Выделение здания под мышью
        grid_height = ROWS * GRID_SIZE
        grid_width = COLS * GRID_SIZE

        if 0 <= y < grid_height and 0 <= x < grid_width:
            # Преобразуем координаты в индексы сетки
            row = int(y // GRID_SIZE)
            col = int(x // GRID_SIZE)

            # Проверяем, что индексы в пределах допустимого
            if 0 <= row < ROWS and 0 <= col < COLS:
                self.selected_building = self.grid[row][col]
            else:
                self.selected_building = None
        else:
            self.selected_building = None

    def on_mouse_press(self, x: float, y: float, button, modifiers):
        # Преобразуем координаты в целые числа
        x_int = int(x)
        y_int = int(y)

        grid_height = ROWS * GRID_SIZE
        grid_width = COLS * GRID_SIZE
        building_map = {
            1: Mine, 2: CoalMine, 3: Smelter, 4: SteelMill,
            5: Conveyor, 6: ElectronicsFactory,
            7: ComputerFactory, 8: Warehouse,
            'M': Market
        }
        if y_int >= grid_height or x_int >= grid_width:
            return

        # Преобразуем координаты в индексы сетки
        row = int(y_int // GRID_SIZE)
        col = int(x_int // GRID_SIZE)

        # Проверяем, что индексы в пределах допустимого
        if row < 0 or row >= ROWS or col < 0 or col >= COLS:
            return
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.grid[row][col] is not None: return

            building_map = {
                1: Mine, 2: CoalMine, 3: Smelter, 4: SteelMill,
                5: Conveyor, 6: ElectronicsFactory,
                7: ComputerFactory, 8: Warehouse,
                'M': Market
            }

            build_class = building_map.get(self.build_mode)
            if build_class:
                if economy.spend(build_class.cost):
                    new_b = build_class(row, col)
                    new_b.direction = self.current_rotation  # Установка направления
                    self.grid[row][col] = new_b

        # ПКМ - удалить здание
        if button == arcade.MOUSE_BUTTON_RIGHT:
            cell = self.grid[row][col]
            if cell:
                refund = cell.cost // 2
                economy.balance += refund
                self.grid[row][col] = None
            return

        # ЛКМ - построить
        if self.grid[row][col]:
            return

        # Определяем класс для строительства

        build_class = building_map.get(self.build_mode)
        if not build_class:
            return

        if economy.spend(build_class.cost):
            self.grid[row][col] = build_class(row, col)

        new_building = build_class(row, col)
        new_building.direction = self.current_rotation
        self.grid[row][col] = new_building

    # ---------------------------------------
    # КЛАВИАТУРА
    # ---------------------------------------
    def on_key_press(self, key, modifiers):
        if key == arcade.key.S:
            self.simulation_running = not self.simulation_running
        elif key == arcade.key.R:
            self.grid = [[None for _ in range(COLS)] for _ in range(ROWS)]

        # Выбор построек
        if key == arcade.key.TAB:  # Вращение по нажатию Tab
            dirs = [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP]
            current_idx = dirs.index(self.current_rotation)
            self.current_rotation = dirs[(current_idx + 1) % 4]
        elif key == arcade.key.KEY_1:
            self.build_mode = 1
        elif key == arcade.key.KEY_2:
            self.build_mode = 2
        elif key == arcade.key.KEY_3:
            self.build_mode = 3
        elif key == arcade.key.KEY_4:
            self.build_mode = 4
        elif key == arcade.key.KEY_5:
            self.build_mode = 5
        elif key == arcade.key.KEY_6:
            self.build_mode = 6
        elif key == arcade.key.KEY_7:
            self.build_mode = 7
        elif key == arcade.key.KEY_8:
            self.build_mode = 8
        elif key == arcade.key.KEY_9:
            self.build_mode = 9
        elif key == arcade.key.KEY_0:
            self.build_mode = 0
        elif key == arcade.key.M:
            self.build_mode = 'M'
        elif key == arcade.key.ESCAPE:
            self.build_mode = None


if __name__ == "__main__":
    game = MyGame()
    arcade.run()
