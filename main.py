"""
Главный файл запуска приложения для сравнения AWR и pg_profile отчетов
"""
import sys
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, str(Path(__file__).parent))

from src.gui import run_gui


def main():
    """Точка входа в приложение"""
    print("Запуск приложения для сравнения AWR и pg_profile отчетов...")
    print("Версия: 1.0.0")
    print("-" * 60)
    
    try:
        run_gui()
    except Exception as e:
        print(f"Ошибка при запуске приложения: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
