"""
Модуль для загрузки конфигурационных файлов
"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """Класс для загрузки и управления конфигурацией приложения"""
    
    def __init__(self, config_dir: str = "config"):
        """
        Инициализация загрузчика конфигурации
        
        Args:
            config_dir: Директория с конфигурационными файлами
        """
        self.config_dir = Path(config_dir)
        self._configs = {}
        
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """
        Загрузка конфигурационного файла
        
        Args:
            config_name: Имя конфигурационного файла (без расширения)
            
        Returns:
            Словарь с конфигурацией
        """
        if config_name in self._configs:
            return self._configs[config_name]
            
        config_path = self.config_dir / f"{config_name}.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        self._configs[config_name] = config
        return config
    
    def get_cross_platform_mapping(self) -> Dict[str, Any]:
        """Получить маппинг метрик для кросс-платформенного сравнения"""
        return self.load_config('cross_platform_mapping')
    
    def get_default_comparison_settings(self) -> Dict[str, Any]:
        """Получить настройки сравнения по умолчанию"""
        return self.load_config('default_comparison')
    
    def get_metric_mapping(self, from_platform: str, to_platform: str) -> Dict[str, list]:
        """
        Получить маппинг метрик между платформами
        
        Args:
            from_platform: Исходная платформа (oracle/postgres)
            to_platform: Целевая платформа (oracle/postgres)
            
        Returns:
            Словарь с маппингом метрик
        """
        mapping_config = self.get_cross_platform_mapping()
        
        if from_platform == to_platform:
            return {}
            
        mapping_key = f"{from_platform}_to_{to_platform}"
        return mapping_config['metric_mapping'].get(mapping_key, {})
    
    def get_available_tables(self, report_type: str) -> list:
        """
        Получить список доступных таблиц для типа отчета
        
        Args:
            report_type: Тип отчета (oracle_awr/postgresql_pg_profile)
            
        Returns:
            Список названий таблиц
        """
        mapping_config = self.get_cross_platform_mapping()
        return mapping_config['available_tables_by_report_type'].get(report_type, [])
    
    def get_thresholds(self, comparison_type: str) -> Dict[str, int]:
        """
        Получить пороговые значения для типа сравнения
        
        Args:
            comparison_type: Тип сравнения (same_platform/cross_platform)
            
        Returns:
            Словарь с пороговыми значениями
        """
        settings = self.get_default_comparison_settings()
        return settings['thresholds'].get(comparison_type, {})
    
    def get_table_description(self, table_name: str) -> str:
        """
        Получить описание таблицы
        
        Args:
            table_name: Название таблицы
            
        Returns:
            Описание таблицы на русском языке
        """
        mapping_config = self.get_cross_platform_mapping()
        descriptions = mapping_config.get('table_descriptions', {})
        return descriptions.get(table_name, table_name)


# Глобальный экземпляр загрузчика конфигурации
config_loader = ConfigLoader()
