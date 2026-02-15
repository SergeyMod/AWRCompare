"""
Движок сравнения отчетов
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..parsers import BaseReportParser, TableData
from ..utils import config_loader


class ComparisonType(Enum):
    """Тип сравнения"""
    ORACLE_ORACLE = "oracle_oracle"
    POSTGRES_POSTGRES = "postgres_postgres"
    CROSS_PLATFORM = "cross_platform"


@dataclass
class ComparisonResult:
    """Результат сравнения одной метрики"""
    metric_name: str
    base_value: Any
    target_value: Any
    absolute_change: Optional[float]
    percent_change: Optional[float]
    is_warning: bool
    is_critical: bool
    
    def get_indicator(self) -> str:
        """Получить индикатор изменения"""
        if self.absolute_change is None:
            return "="
        elif self.absolute_change > 0:
            return "↑"
        elif self.absolute_change < 0:
            return "↓"
        else:
            return "="


@dataclass
class TableComparison:
    """Результат сравнения таблицы"""
    table_name: str
    table_description: str
    base_table: TableData
    target_table: TableData
    comparisons: List[ComparisonResult]
    
    def get_critical_count(self) -> int:
        """Количество критических отклонений"""
        return sum(1 for c in self.comparisons if c.is_critical)
    
    def get_warning_count(self) -> int:
        """Количество предупреждений"""
        return sum(1 for c in self.comparisons if c.is_warning and not c.is_critical)


class ComparisonEngine:
    """Движок для сравнения отчетов о производительности БД"""
    
    def __init__(self):
        self.config = config_loader
        
    def compare_reports(
        self,
        base_parser: BaseReportParser,
        target_parser: BaseReportParser,
        selected_tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Сравнение двух отчетов
        
        Args:
            base_parser: Парсер базового отчета
            target_parser: Парсер целевого отчета
            selected_tables: Список таблиц для сравнения (None = все доступные)
            
        Returns:
            Словарь с результатами сравнения
        """
        # Определение типа сравнения
        comparison_type = self._determine_comparison_type(
            base_parser.metadata.report_type,
            target_parser.metadata.report_type
        )
        
        # Получение пороговых значений
        thresholds = self._get_thresholds(comparison_type)
        
        # Определение таблиц для сравнения
        if selected_tables is None:
            selected_tables = self._get_common_tables(base_parser, target_parser)
        
        # Сравнение таблиц
        table_comparisons = []
        for table_name in selected_tables:
            base_table = base_parser.get_table(table_name)
            target_table = target_parser.get_table(table_name)
            
            if base_table and target_table:
                comparison = self._compare_tables(
                    table_name,
                    base_table,
                    target_table,
                    thresholds,
                    comparison_type
                )
                if comparison:
                    table_comparisons.append(comparison)
        
        # Формирование итогового результата
        return {
            'comparison_type': comparison_type.value,
            'base_metadata': base_parser.metadata,
            'target_metadata': target_parser.metadata,
            'table_comparisons': table_comparisons,
            'thresholds': thresholds,
            'summary': self._generate_summary(table_comparisons)
        }
    
    def _determine_comparison_type(
        self,
        base_type: str,
        target_type: str
    ) -> ComparisonType:
        """Определение типа сравнения"""
        if base_type == target_type:
            if 'oracle' in base_type:
                return ComparisonType.ORACLE_ORACLE
            else:
                return ComparisonType.POSTGRES_POSTGRES
        else:
            return ComparisonType.CROSS_PLATFORM
    
    def _get_thresholds(self, comparison_type: ComparisonType) -> Dict[str, int]:
        """Получение пороговых значений"""
        if comparison_type == ComparisonType.CROSS_PLATFORM:
            return self.config.get_thresholds('cross_platform')
        else:
            return self.config.get_thresholds('same_platform')
    
    def _get_common_tables(
        self,
        base_parser: BaseReportParser,
        target_parser: BaseReportParser
    ) -> List[str]:
        """Получение списка общих таблиц"""
        base_tables = set(base_parser.get_available_tables())
        target_tables = set(target_parser.get_available_tables())
        return list(base_tables & target_tables)
    
    def _compare_tables(
        self,
        table_name: str,
        base_table: TableData,
        target_table: TableData,
        thresholds: Dict[str, int],
        comparison_type: ComparisonType
    ) -> Optional[TableComparison]:
        """Сравнение двух таблиц"""
        comparisons = []
        
        # Получение описания таблицы
        table_description = self.config.get_table_description(table_name)
        
        # Сравнение построчно
        if comparison_type == ComparisonType.CROSS_PLATFORM:
            # Кросс-платформенное сравнение с маппингом метрик
            comparisons = self._compare_cross_platform(
                base_table,
                target_table,
                thresholds
            )
        else:
            # Прямое сравнение
            comparisons = self._compare_same_platform(
                base_table,
                target_table,
                thresholds
            )
        
        if not comparisons:
            return None
        
        return TableComparison(
            table_name=table_name,
            table_description=table_description,
            base_table=base_table,
            target_table=target_table,
            comparisons=comparisons
        )
    
    def _compare_same_platform(
        self,
        base_table: TableData,
        target_table: TableData,
        thresholds: Dict[str, int]
    ) -> List[ComparisonResult]:
        """Сравнение таблиц одной платформы"""
        comparisons = []
        
        # Создание индекса для быстрого поиска
        target_index = {self._get_row_key(row): row for row in target_table.rows}
        
        for base_row in base_table.rows:
            row_key = self._get_row_key(base_row)
            target_row = target_index.get(row_key)
            
            if target_row:
                # Сравнение значений в строке
                for header in base_table.headers:
                    if header in target_row and self._is_numeric_column(header):
                        base_value = base_row.get(header)
                        target_value = target_row.get(header)
                        
                        if base_value is not None and target_value is not None:
                            comparison = self._compare_values(
                                header,
                                base_value,
                                target_value,
                                thresholds
                            )
                            comparisons.append(comparison)
        
        return comparisons
    
    def _compare_cross_platform(
        self,
        base_table: TableData,
        target_table: TableData,
        thresholds: Dict[str, int]
    ) -> List[ComparisonResult]:
        """Кросс-платформенное сравнение с маппингом метрик"""
        comparisons = []
        
        # Получение маппинга метрик
        # Упрощенная версия - прямое сравнение по общим метрикам
        common_headers = set(base_table.headers) & set(target_table.headers)
        
        for header in common_headers:
            if self._is_numeric_column(header):
                # Агрегация значений по столбцу
                base_values = [row.get(header) for row in base_table.rows if row.get(header) is not None]
                target_values = [row.get(header) for row in target_table.rows if row.get(header) is not None]
                
                if base_values and target_values:
                    base_avg = sum(base_values) / len(base_values)
                    target_avg = sum(target_values) / len(target_values)
                    
                    comparison = self._compare_values(
                        header,
                        base_avg,
                        target_avg,
                        thresholds
                    )
                    comparisons.append(comparison)
        
        return comparisons
    
    def _compare_values(
        self,
        metric_name: str,
        base_value: Any,
        target_value: Any,
        thresholds: Dict[str, int]
    ) -> ComparisonResult:
        """Сравнение двух значений"""
        # Преобразование в числа
        try:
            base_num = float(base_value)
            target_num = float(target_value)
        except (ValueError, TypeError):
            return ComparisonResult(
                metric_name=metric_name,
                base_value=base_value,
                target_value=target_value,
                absolute_change=None,
                percent_change=None,
                is_warning=False,
                is_critical=False
            )
        
        # Вычисление изменений
        absolute_change = target_num - base_num
        
        if base_num != 0:
            percent_change = (absolute_change / abs(base_num)) * 100
        else:
            percent_change = None
        
        # Определение уровня критичности
        is_warning = False
        is_critical = False
        
        if percent_change is not None:
            abs_percent = abs(percent_change)
            warning_threshold = thresholds.get('warning_percent', 15)
            critical_threshold = thresholds.get('critical_percent', 30)
            
            if abs_percent >= critical_threshold:
                is_critical = True
            elif abs_percent >= warning_threshold:
                is_warning = True
        
        return ComparisonResult(
            metric_name=metric_name,
            base_value=base_value,
            target_value=target_value,
            absolute_change=absolute_change,
            percent_change=percent_change,
            is_warning=is_warning,
            is_critical=is_critical
        )
    
    def _get_row_key(self, row: Dict[str, Any]) -> str:
        """Получение ключа строки для индексации"""
        # Используем первое значение как ключ (обычно это имя метрики или SQL ID)
        first_value = next(iter(row.values()), "")
        return str(first_value)
    
    def _is_numeric_column(self, column_name: str) -> bool:
        """Проверка, является ли столбец числовым"""
        # Игнорируемые столбцы
        ignored = self.config.get_default_comparison_settings().get('ignored_columns', [])
        if column_name in ignored:
            return False
        
        # Столбцы с текстовыми данными
        text_columns = ['Metric', 'Event', 'SQL ID', 'Query ID', 'Name', 'Description']
        return column_name not in text_columns
    
    def _generate_summary(self, table_comparisons: List[TableComparison]) -> Dict[str, Any]:
        """Генерация сводки по результатам сравнения"""
        total_comparisons = sum(len(tc.comparisons) for tc in table_comparisons)
        total_critical = sum(tc.get_critical_count() for tc in table_comparisons)
        total_warnings = sum(tc.get_warning_count() for tc in table_comparisons)
        
        return {
            'total_tables': len(table_comparisons),
            'total_comparisons': total_comparisons,
            'critical_count': total_critical,
            'warning_count': total_warnings,
            'has_issues': total_critical > 0 or total_warnings > 0
        }
