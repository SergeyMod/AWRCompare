"""
Базовый класс для парсеров отчетов
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReportMetadata:
    """Метаданные отчета"""
    report_type: str  # 'oracle_awr' или 'postgresql_pg_profile'
    version: str
    database_name: str
    instance_name: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_minutes: Optional[float]
    
    def __str__(self):
        return f"{self.report_type} - {self.database_name} ({self.version})"


@dataclass
class TableData:
    """Данные таблицы из отчета"""
    name: str
    headers: List[str]
    rows: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    def __len__(self):
        return len(self.rows)
    
    def is_empty(self):
        return len(self.rows) == 0


class BaseReportParser(ABC):
    """Базовый класс для парсеров отчетов о производительности БД"""
    
    def __init__(self, file_path: str):
        """
        Инициализация парсера
        
        Args:
            file_path: Путь к файлу отчета
        """
        self.file_path = file_path
        self.metadata: Optional[ReportMetadata] = None
        self.tables: Dict[str, TableData] = {}
        self._raw_content: Optional[str] = None
        
    @abstractmethod
    def parse(self) -> bool:
        """
        Парсинг отчета
        
        Returns:
            True если парсинг успешен, False иначе
        """
        pass
    
    @abstractmethod
    def extract_metadata(self) -> ReportMetadata:
        """
        Извлечение метаданных отчета
        
        Returns:
            Объект с метаданными
        """
        pass
    
    @abstractmethod
    def extract_table(self, table_name: str) -> Optional[TableData]:
        """
        Извлечение данных конкретной таблицы
        
        Args:
            table_name: Название таблицы
            
        Returns:
            Объект с данными таблицы или None
        """
        pass
    
    def get_available_tables(self) -> List[str]:
        """
        Получить список доступных таблиц в отчете
        
        Returns:
            Список названий таблиц
        """
        return list(self.tables.keys())
    
    def get_table(self, table_name: str) -> Optional[TableData]:
        """
        Получить данные таблицы
        
        Args:
            table_name: Название таблицы
            
        Returns:
            Объект с данными таблицы или None
        """
        return self.tables.get(table_name)
    
    def _read_file(self) -> str:
        """
        Чтение содержимого файла
        
        Returns:
            Содержимое файла
        """
        if self._raw_content is None:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                self._raw_content = f.read()
        return self._raw_content
    
    def _normalize_value(self, value: str) -> Any:
        """
        Нормализация значения (преобразование строки в число если возможно)
        
        Args:
            value: Строковое значение
            
        Returns:
            Нормализованное значение
        """
        if not value or value.strip() == '':
            return None
            
        value = value.strip()
        
        # Удаление запятых из чисел (например, 1,234.56 -> 1234.56)
        value_clean = value.replace(',', '')
        
        # Попытка преобразовать в число
        try:
            if '.' in value_clean:
                return float(value_clean)
            else:
                return int(value_clean)
        except ValueError:
            pass
        
        # Обработка процентов
        if value.endswith('%'):
            try:
                return float(value[:-1].replace(',', ''))
            except ValueError:
                pass
        
        # Обработка единиц измерения (K, M, G, T)
        multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
        for suffix, multiplier in multipliers.items():
            if value_clean.endswith(suffix):
                try:
                    return float(value_clean[:-1]) * multiplier
                except ValueError:
                    pass
        
        return value
