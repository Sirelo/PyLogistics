import arcade
import random
import math
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
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
        self.item = None
        self.timer = 0.0
        self.progress = 0.0
        self.efficiency = 1.0
        self.production_queue = []

    def can_accept(self, item_type: ResourceType) -> bool:
        return self.item is None and item_type in self.input_types

    def accept_item(self, item_type: ResourceType) -> bool:
        if self.can_accept(item_type):
            self.item = item_type
            return True
        return False

    def can_give_item(self) -> bool:
        return self.item is not None and self.item == self.output_type

    def charge_upkeep(self):
        economy.spend(self.upkeep)

    def do_cycle(self, delta_time: float) -> bool:
        self.timer += delta_time
        if self.timer >= self.cycle_time:
            self.timer = 0.0
            return True
        return False

    def process(self, grid):
        pass


# =========================================================
#                   ПРОМЫШЛЕННЫЕ МОДУЛИ
# =========================================================
class Mine(Building):
    cost = 300
    upkeep = 5
    cycle_time = 3.0
    output_type = ResourceType.ORE

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.animation_phase = 0.0

    def process(self, grid):
        self.animation_phase += 0.1
        if self.do_cycle(1 / 60):
            self.charge_upkeep()
            if self.item is None and economy.spend(20):
                self.item = ResourceType.ORE
                economy.track_production(ResourceType.ORE, 20)


class CoalMine(Building):
    cost = 350
    upkeep = 7
    cycle_time = 2.5
    output_type = ResourceType.COAL

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.smoke_offset = random.random() * 100

    def process(self, grid):
        if self.do_cycle(1 / 60):
            self.charge_upkeep()
            if self.item is None and economy.spend(15):
                self.item = ResourceType.COAL
                economy.track_production(ResourceType.COAL, 15)


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

    def can_accept(self, item_type: ResourceType) -> bool:
        return (self.input_a is None or self.input_b is None) and item_type in self.input_types

    def accept_item(self, item_type: ResourceType) -> bool:
        if self.can_accept(item_type):
            if self.input_a is None:
                self.input_a = item_type
            else:
                self.input_b = item_type
            return True
        return False

    def process(self, grid):
        if self.input_a and self.input_b and not self.is_active:
            self.is_active = True
            self.progress = 0.0

        if self.is_active:
            self.progress += 1 / 60
            self.heat = min(100.0, self.heat + 2.0)
            if self.progress >= self.cycle_time:
                self.item = ResourceType.IRON
                self.input_a = None
                self.input_b = None
                self.is_active = False
                self.progress = 0.0
                economy.track_production(ResourceType.IRON, self.production_cost)
                self.charge_upkeep()
        else:
            self.heat = max(0.0, self.heat - 0.5)


class SteelMill(Building):
    cost = 1200
    upkeep = 25
    cycle_time = 5.0
    input_types = [ResourceType.IRON, ResourceType.COAL]
    output_type = ResourceType.STEEL
    production_cost = 100

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.temperature = 0.0
        self.flame_intensity = 0.0

    def process(self, grid):
        if self.do_cycle(1 / 60) and self.item is None:
            self.charge_upkeep()
            self.temperature = 100.0
            self.flame_intensity = 50.0
            if economy.spend(self.production_cost):
                self.item = ResourceType.STEEL
                economy.track_production(ResourceType.STEEL, self.production_cost)
        else:
            self.temperature = max(0.0, self.temperature - 0.5)
            self.flame_intensity = max(0.0, self.flame_intensity - 1.0)


class AssemblyLine(Building):
    cost = 2000
    upkeep = 40
    cycle_time = 6.0
    input_types = [ResourceType.STEEL, ResourceType.ELECTRONICS]
    output_type = ResourceType.CAR
    production_cost = 500

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.assembly_progress = 0.0
        self.conveyor_position = 0.0

    def process(self, grid):
        self.conveyor_position = (self.conveyor_position + 0.5) % 100
        if self.do_cycle(1 / 60) and self.item is None:
            self.charge_upkeep()
            if economy.spend(self.production_cost):
                self.item = ResourceType.CAR
                economy.track_production(ResourceType.CAR, self.production_cost)


class ElectronicsFactory(Building):
    cost = 1500
    upkeep = 30
    cycle_time = 4.0
    input_types = [ResourceType.COPPER, ResourceType.CIRCUIT]
    output_type = ResourceType.ELECTRONICS
    production_cost = 300

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.light_pulse = 0.0

    def process(self, grid):
        self.light_pulse = (self.light_pulse + 5.0) % 100
        if self.do_cycle(1 / 60) and self.item is None:
            self.charge_upkeep()
            if economy.spend(self.production_cost):
                self.item = ResourceType.ELECTRONICS
                economy.track_production(ResourceType.ELECTRONICS, self.production_cost)


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

    def process(self, grid):
        self.arm_rotation = (self.arm_rotation + 2.0) % 360
        if self.do_cycle(1 / 60) and self.item is None:
            self.charge_upkeep()
            if economy.spend(self.production_cost):
                self.item = ResourceType.ROBOT
                economy.track_production(ResourceType.ROBOT, self.production_cost)
                self.is_assembling = True
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
        self.screen_flash = 0.0

    def process(self, grid):
        self.screen_flash = (self.screen_flash + 3.0) % 100
        if self.do_cycle(1 / 60) and self.item is None:
            self.charge_upkeep()
            if economy.spend(self.production_cost):
                self.item = ResourceType.COMPUTER
                economy.track_production(ResourceType.COMPUTER, self.production_cost)


class Conveyor(Building):
    cost = 100
    upkeep = 1
    cycle_time = 0.5

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.belt_speed = 0.5
        self.belt_position = random.random() * 100

    def process(self, grid):
        self.belt_position = (self.belt_position + self.belt_speed) % 100
        if not self.do_cycle(1 / 60):
            return

        # Принимаем предмет слева
        if self.item is None:
            left_col = self.col - 1
            if left_col >= 0:
                left_cell = grid[self.row][left_col]
                if left_cell and left_cell.can_give_item():
                    self.item = left_cell.item
                    left_cell.item = None

        # Передаем предмет вправо
        if self.item:
            next_col = self.col + 1
            if next_col < COLS:
                next_cell = grid[self.row][next_col]
                if next_cell and next_cell.can_accept(self.item):
                    if next_cell.accept_item(self.item):
                        self.item = None


class Warehouse(Building):
    cost = 500
    upkeep = 10
    capacity = 10

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.storage = []
        self.stored_types = {rt: 0 for rt in ResourceType}

    def can_accept(self, item_type: ResourceType) -> bool:
        return len(self.storage) < self.capacity

    def accept_item(self, item_type: ResourceType) -> bool:
        if self.can_accept(item_type):
            self.storage.append(item_type)
            self.stored_types[item_type] += 1
            return True
        return False

    def can_give_item(self) -> bool:
        return len(self.storage) > 0

    def process(self, grid):
        if self.do_cycle(2.0) and self.item is None and self.storage:
            self.item = self.storage.pop(0)
            self.stored_types[self.item] -= 1


class Market(Building):
    cost = 400
    upkeep = 8
    cycle_time = 2.0

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.sell_prices = {
            ResourceType.ORE: 80,
            ResourceType.COAL: 50,
            ResourceType.IRON: 150,
            ResourceType.STEEL: 350,
            ResourceType.COPPER: 200,
            ResourceType.CIRCUIT: 600,
            ResourceType.ELECTRONICS: 1500,
            ResourceType.ENGINE: 1000,
            ResourceType.ROBOT: 2000,
            ResourceType.CAR: 6000,
            ResourceType.COMPUTER: 4000,
        }

    def can_accept(self, item_type: ResourceType) -> bool:
        return self.item is None and item_type in self.sell_prices

    def process(self, grid):
        if self.do_cycle(1 / 60):
            self.charge_upkeep()
            if self.item:
                price = self.sell_prices.get(self.item, 0)
                economy.earn(price, self.item)
                self.item = None


# =========================================================
#                     ИГРА
# =========================================================
class MyGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        self.grid: List[List[Optional[Building]]] = [
            [None for _ in range(COLS)] for _ in range(ROWS)
        ]

        self.simulation_running = False
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
            (6, "Сборочная линия", AssemblyLine, 2000),
            (7, "Электронный завод", ElectronicsFactory, 1500),
            (8, "Завод роботов", RobotFactory, 3000),
            (9, "Компьютерный завод", ComputerFactory, 2500),
            (0, "Склад", Warehouse, 500),
            ('M', "Рынок", Market, 400),
        ]

        # Инициализация примера производства
        self.create_example_factory()

    def create_example_factory(self):
        """Создаем пример производственной цепочки"""
        center_row = ROWS // 2
        center_col = COLS // 2 - 3

        # Руда -> Железо -> Сталь -> Машины
        self.grid[center_row][center_col] = Mine(center_row, center_col)
        self.grid[center_row][center_col + 1] = Conveyor(center_row, center_col + 1)
        self.grid[center_row][center_col + 2] = Smelter(center_row, center_col + 2)
        self.grid[center_row][center_col + 3] = Conveyor(center_row, center_col + 3)
        self.grid[center_row][center_col + 4] = SteelMill(center_row, center_col + 4)
        self.grid[center_row][center_col + 5] = Conveyor(center_row, center_col + 5)
        self.grid[center_row][center_col + 6] = AssemblyLine(center_row, center_col + 6)
        self.grid[center_row][center_col + 7] = Conveyor(center_row, center_col + 7)
        self.grid[center_row][center_col + 8] = Market(center_row, center_col + 8)

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

            # Подсказка при наведении
            mouse_x, mouse_y = self.mouse_x, self.mouse_y
            if x <= mouse_x <= x + building_size and building_panel_y <= mouse_y <= building_panel_y + building_size:
                self.draw_tooltip(mouse_x, mouse_y, f"{name}\nСтоимость: ${cost}\nUpkeep: ${building_class.upkeep}")

        # Информация о выбранном здании
        if self.selected_building:
            self.draw_building_info(self.selected_building)

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
        """Рисуем одно здание с анимацией"""
        # Фон здания
        if isinstance(building, Mine):
            color = (139, 69, 19)  # Коричневый
        elif isinstance(building, CoalMine):
            color = (34, 34, 34)  # Темно-серый
        elif isinstance(building, Smelter):
            color = (255, 140, 0)  # Оранжевый
            # Анимация пламени
            if building.is_active:
                flame_height = 10 + math.sin(building.heat * 0.1) * 5
                for i in range(3):
                    flame_x = x + GRID_SIZE // 2 + (i - 1) * 8
                    flame_y = y + 5
                    arcade.draw_triangle_filled(
                        flame_x, flame_y,
                        flame_x - 4, flame_y + flame_height,
                        flame_x + 4, flame_y + flame_height,
                        (255, 69, 0)
                    )
        elif isinstance(building, SteelMill):
            color = (192, 192, 192)  # Серебряный
        elif isinstance(building, AssemblyLine):
            color = (220, 20, 60)  # Красный
            # Анимация конвейера
            for i in range(3):
                belt_y = y + 10 + i * 10
                belt_pos = int((building.conveyor_position + i * 20) % GRID_SIZE)
                arcade.draw_line(x + belt_pos, belt_y, x + belt_pos + 15, belt_y,
                                 (100, 100, 100), 3)
        elif isinstance(building, RobotFactory):
            color = (0, 191, 255)  # Голубой
            # Анимация роборуки
            arm_length = 15
            arm_x = int(x + GRID_SIZE // 2 + math.cos(math.radians(building.arm_rotation)) * arm_length)
            arm_y = int(y + GRID_SIZE // 2 + math.sin(math.radians(building.arm_rotation)) * arm_length)
            arcade.draw_line(x + GRID_SIZE // 2, y + GRID_SIZE // 2, arm_x, arm_y,
                             (255, 255, 255), 3)
        elif isinstance(building, Warehouse):
            color = (160, 82, 45)  # Сиена
            # Показываем заполненность склада
            if hasattr(building, 'storage'):
                fill_level = len(building.storage) / building.capacity
                arcade.draw_lbwh_rectangle_filled(x + 5, y + 5,
                                                  int((GRID_SIZE - 10) * fill_level),
                                                  GRID_SIZE - 10,
                                                  (139, 69, 19))
        elif isinstance(building, Market):
            color = (152, 195, 121)  # Зеленый
            # Анимация денег
            coin_y = int(y + 15 + math.sin(self.day_timer * 2) * 3)
            arcade.draw_circle_filled(x + GRID_SIZE // 2, coin_y, 5, (255, 215, 0))
        else:
            color = (100, 100, 100)  # Серый по умолчанию

        # Основной квадрат здания
        arcade.draw_lbwh_rectangle_filled(x, y, GRID_SIZE, GRID_SIZE, color)

        # Обводка
        arcade.draw_lbwh_rectangle_outline(x, y, GRID_SIZE, GRID_SIZE,
                                           (255, 255, 255, 100), 2)

        # Тень для объема
        arcade.draw_lbwh_rectangle_filled(x + 2, y - 2, GRID_SIZE - 4, 4, (0, 0, 0, 50))

        # Иконка ресурса если есть
        if building.item:
            resource = RESOURCES[building.item]
            arcade.draw_text(resource.icon, x + GRID_SIZE // 2 - 6, y + GRID_SIZE // 2 - 8,
                             resource.color, 20)

            # Анимация движения для конвейеров
            if isinstance(building, Conveyor):
                offset = int((building.belt_position / 100) * GRID_SIZE)
                arcade.draw_text(resource.icon, x + offset - 6, y + GRID_SIZE // 2 - 8,
                                 resource.color, 20)

    # ---------------------------------------
    # ОСНОВНОЕ РИСОВАНИЕ
    # ---------------------------------------
    def on_draw(self):
        self.clear()

        # Фон
        arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (25, 25, 35))

        # Сетка
        self.draw_grid_background()

        # Линии сетки
        for r in range(ROWS + 1):
            arcade.draw_line(0, r * GRID_SIZE, SCREEN_WIDTH, r * GRID_SIZE,
                             self.ui_colors['bg_light'], 1)
        for c in range(COLS + 1):
            arcade.draw_line(c * GRID_SIZE, 0, c * GRID_SIZE, ROWS * GRID_SIZE,
                             self.ui_colors['bg_light'], 1)

        # Здания
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                if cell:
                    x = c * GRID_SIZE
                    y = r * GRID_SIZE
                    self.draw_building(cell, x, y)

        # UI
        self.draw_ui_panel()
        self.draw_resource_legend()

        # Заголовок
        arcade.draw_text("🏭 ПРОМЫШЛЕННЫЙ КОМПЛЕКС", SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 40,
                         self.ui_colors['primary'], 24, bold=True)

        # Управление
        controls_text = [
            "⚙️ УПРАВЛЕНИЕ:",
            "1-9,0,M - Выбор постройки",
            "ЛКМ - Построить | ПКМ - Удалить",
            "S - Старт/Стоп | SPACE - Шаг",
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

        # Игровое время
        self.day_timer += delta_time * self.time_scale
        if self.day_timer >= self.day_length:
            self.day_timer = 0
            economy.daily_profit = economy.total_sales - int(economy.total_production * 0.7)

        # Обновление всех зданий
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                if cell:
                    cell.process(self.grid)

    def simulate_step(self):
        """Один шаг симуляции"""
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                if cell:
                    if hasattr(cell, 'timer'):
                        cell.timer = cell.cycle_time
                    cell.process(self.grid)

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

        if y_int >= grid_height or x_int >= grid_width:
            return

        # Преобразуем координаты в индексы сетки
        row = int(y_int // GRID_SIZE)
        col = int(x_int // GRID_SIZE)

        # Проверяем, что индексы в пределах допустимого
        if row < 0 or row >= ROWS or col < 0 or col >= COLS:
            return

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
        building_map = {
            1: Mine, 2: CoalMine, 3: Smelter, 4: SteelMill,
            5: Conveyor, 6: AssemblyLine, 7: ElectronicsFactory,
            8: RobotFactory, 9: ComputerFactory, 0: Warehouse,
            'M': Market
        }

        build_class = building_map.get(self.build_mode)
        if not build_class:
            return

        if economy.spend(build_class.cost):
            self.grid[row][col] = build_class(row, col)

    # ---------------------------------------
    # КЛАВИАТУРА
    # ---------------------------------------
    def on_key_press(self, key, modifiers):
        if key == arcade.key.S:
            self.simulation_running = not self.simulation_running
        elif key == arcade.key.SPACE:
            self.simulate_step()
        elif key == arcade.key.R:
            # Сброс примера
            self.grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
            self.create_example_factory()

        # Выбор построек
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