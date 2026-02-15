"""
Базовые тесты для проверки работоспособности модулей
"""
import sys
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import config_loader
from src.parsers import BaseReportParser, ReportMetadata, TableData
from src.comparison import ComparisonEngine, ComparisonType
from src.report_generator import ReportGenerator


def test_config_loader():
    """Тест загрузки конфигурации"""
    print("Тест загрузки конфигурации...")
    
    try:
        # Загрузка маппинга
        mapping = config_loader.get_cross_platform_mapping()
        assert 'metric_mapping' in mapping
        print("✓ Маппинг метрик загружен")
        
        # Загрузка настроек
        settings = config_loader.get_default_comparison_settings()
        assert 'thresholds' in settings
        print("✓ Настройки сравнения загружены")
        
        # Получение доступных таблиц
        tables = config_loader.get_available_tables('oracle_awr')
        assert len(tables) > 0
        print(f"✓ Доступно таблиц для Oracle AWR: {len(tables)}")
        
        # Получение пороговых значений
        thresholds = config_loader.get_thresholds('same_platform')
        assert 'warning_percent' in thresholds
        print(f"✓ Пороговые значения: warning={thresholds['warning_percent']}%, critical={thresholds['critical_percent']}%")
        
        print("✓ Все тесты конфигурации пройдены\n")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка в тестах конфигурации: {e}\n")
        return False


def test_report_metadata():
    """Тест создания метаданных отчета"""
    print("Тест метаданных отчета...")
    
    try:
        metadata = ReportMetadata(
            report_type='oracle_awr',
            version='19c',
            database_name='PROD',
            instance_name='PROD1',
            start_time=None,
            end_time=None,
            duration_minutes=None
        )
        
        assert metadata.report_type == 'oracle_awr'
        assert metadata.database_name == 'PROD'
        print(f"✓ Метаданные созданы: {metadata}")
        print("✓ Тест метаданных пройден\n")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка в тесте метаданных: {e}\n")
        return False


def test_table_data():
    """Тест создания данных таблицы"""
    print("Тест данных таблицы...")
    
    try:
        table = TableData(
            name='load_profile',
            headers=['Metric', 'Value'],
            rows=[
                {'Metric': 'DB Time', 'Value': 1000},
                {'Metric': 'CPU Time', 'Value': 800}
            ],
            metadata={}
        )
        
        assert len(table) == 2
        assert not table.is_empty()
        print(f"✓ Таблица создана: {table.name}, строк: {len(table)}")
        print("✓ Тест данных таблицы пройден\n")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка в тесте данных таблицы: {e}\n")
        return False


def test_comparison_engine():
    """Тест движка сравнения"""
    print("Тест движка сравнения...")
    
    try:
        engine = ComparisonEngine()
        
        # Проверка определения типа сравнения
        comp_type = engine._determine_comparison_type('oracle_awr', 'oracle_awr')
        assert comp_type == ComparisonType.ORACLE_ORACLE
        print("✓ Определение типа сравнения работает")
        
        # Проверка получения пороговых значений
        thresholds = engine._get_thresholds(ComparisonType.ORACLE_ORACLE)
        assert 'warning_percent' in thresholds
        print("✓ Получение пороговых значений работает")
        
        print("✓ Тест движка сравнения пройден\n")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка в тесте движка сравнения: {e}\n")
        return False


def test_report_generator():
    """Тест генератора отчетов"""
    print("Тест генератора отчетов...")
    
    try:
        generator = ReportGenerator()
        
        # Создание тестовых данных
        from src.comparison import ComparisonResult, TableComparison
        
        comp_result = ComparisonResult(
            metric_name='DB Time',
            base_value=1000,
            target_value=1200,
            absolute_change=200,
            percent_change=20.0,
            is_warning=True,
            is_critical=False
        )
        
        table_comp = TableComparison(
            table_name='load_profile',
            table_description='Профиль нагрузки',
            base_table=TableData('load_profile', ['Metric', 'Value'], [], {}),
            target_table=TableData('load_profile', ['Metric', 'Value'], [], {}),
            comparisons=[comp_result]
        )
        
        test_data = {
            'comparison_type': 'oracle_oracle',
            'base_metadata': ReportMetadata('oracle_awr', '19c', 'PROD', 'PROD1', None, None, None),
            'target_metadata': ReportMetadata('oracle_awr', '19c', 'PROD', 'PROD1', None, None, None),
            'table_comparisons': [table_comp],
            'thresholds': {'warning_percent': 15, 'critical_percent': 30},
            'summary': {
                'total_tables': 1,
                'total_comparisons': 1,
                'critical_count': 0,
                'warning_count': 1,
                'has_issues': True
            }
        }
        
        # Генерация текстового отчета
        text_report = generator.generate_report(test_data, output_format='text')
        assert len(text_report) > 0
        print("✓ Генерация текстового отчета работает")
        
        # Генерация JSON отчета
        json_report = generator.generate_report(test_data, output_format='json')
        assert len(json_report) > 0
        print("✓ Генерация JSON отчета работает")
        
        print("✓ Тест генератора отчетов пройден\n")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка в тесте генератора отчетов: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Запуск всех тестов"""
    print("=" * 60)
    print("ЗАПУСК БАЗОВЫХ ТЕСТОВ")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Загрузка конфигурации", test_config_loader()))
    results.append(("Метаданные отчета", test_report_metadata()))
    results.append(("Данные таблицы", test_table_data()))
    results.append(("Движок сравнения", test_comparison_engine()))
    results.append(("Генератор отчетов", test_report_generator()))
    
    print("=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ ПРОЙДЕН" if result else "✗ ПРОВАЛЕН"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    
    print()
    print(f"Всего тестов: {total}")
    print(f"Пройдено: {passed}")
    print(f"Провалено: {total - passed}")
    print("=" * 60)
    
    return all(r for _, r in results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
