"""
Генератор отчетов о сравнении
"""
import json
import csv
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from ..comparison import TableComparison, ComparisonResult
from ..utils import config_loader


class ReportGenerator:
    """Генератор отчетов о сравнении"""
    
    def __init__(self):
        self.config = config_loader
        
    def generate_report(
        self,
        comparison_data: Dict[str, Any],
        output_format: str = 'text',
        output_path: str = None
    ) -> str:
        """
        Генерация отчета о сравнении
        
        Args:
            comparison_data: Данные сравнения
            output_format: Формат вывода (text, html, csv, json)
            output_path: Путь для сохранения файла
            
        Returns:
            Текст отчета или путь к файлу
        """
        if output_format == 'text':
            report = self._generate_text_report(comparison_data)
        elif output_format == 'html':
            report = self._generate_html_report(comparison_data)
        elif output_format == 'csv':
            report = self._generate_csv_report(comparison_data)
        elif output_format == 'json':
            report = self._generate_json_report(comparison_data)
        else:
            raise ValueError(f"Неподдерживаемый формат: {output_format}")
        
        # Сохранение в файл если указан путь
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            return output_path
        
        return report
    
    def _generate_text_report(self, data: Dict[str, Any]) -> str:
        """Генерация текстового отчета"""
        lines = []
        
        # Заголовок
        lines.append("=" * 80)
        lines.append("ОТЧЕТ О СРАВНЕНИИ ОТЧЕТОВ О ПРОИЗВОДИТЕЛЬНОСТИ БД")
        lines.append("=" * 80)
        lines.append("")
        
        # Информация о сравнении
        comparison_type = data['comparison_type']
        base_meta = data['base_metadata']
        target_meta = data['target_metadata']
        
        lines.append(f"Тип сравнения: {self._format_comparison_type(comparison_type)}")
        lines.append("")
        
        lines.append(f"Базовый отчет:")
        lines.append(f"  Тип: {base_meta.report_type}")
        lines.append(f"  БД: {base_meta.database_name}")
        lines.append(f"  Версия: {base_meta.version}")
        if base_meta.start_time:
            lines.append(f"  Период: {base_meta.start_time} - {base_meta.end_time}")
        lines.append("")
        
        lines.append(f"Целевой отчет:")
        lines.append(f"  Тип: {target_meta.report_type}")
        lines.append(f"  БД: {target_meta.database_name}")
        lines.append(f"  Версия: {target_meta.version}")
        if target_meta.start_time:
            lines.append(f"  Период: {target_meta.start_time} - {target_meta.end_time}")
        lines.append("")
        
        # Сводка
        summary = data['summary']
        lines.append("СВОДКА:")
        lines.append(f"  Сравнено таблиц: {summary['total_tables']}")
        lines.append(f"  Всего метрик: {summary['total_comparisons']}")
        lines.append(f"  Критических отклонений: {summary['critical_count']}")
        lines.append(f"  Предупреждений: {summary['warning_count']}")
        lines.append("")
        
        # Детальное сравнение таблиц
        lines.append("=" * 80)
        lines.append("ДЕТАЛЬНОЕ СРАВНЕНИЕ")
        lines.append("=" * 80)
        lines.append("")
        
        for table_comp in data['table_comparisons']:
            lines.extend(self._format_table_comparison(table_comp))
            lines.append("")
        
        # Пороговые значения
        thresholds = data['thresholds']
        lines.append("=" * 80)
        lines.append("ПОРОГОВЫЕ ЗНАЧЕНИЯ:")
        lines.append(f"  Предупреждение: {thresholds['warning_percent']}%")
        lines.append(f"  Критическое: {thresholds['critical_percent']}%")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _format_table_comparison(self, table_comp: TableComparison) -> List[str]:
        """Форматирование сравнения таблицы"""
        lines = []
        
        lines.append(f"Таблица: {table_comp.table_description}")
        lines.append("-" * 80)
        
        # Заголовок таблицы
        header = f"{'Метрика':<40} {'Базовый':>12} {'Целевой':>12} {'Изменение':>12}"
        lines.append(header)
        lines.append("-" * 80)
        
        # Строки с данными
        for comp in table_comp.comparisons:
            metric = comp.metric_name[:38]
            base_val = self._format_value(comp.base_value)
            target_val = self._format_value(comp.target_value)
            
            if comp.percent_change is not None:
                change = f"{comp.percent_change:+.1f}% {comp.get_indicator()}"
                
                # Добавление индикаторов критичности
                if comp.is_critical:
                    change += " ❗"
                elif comp.is_warning:
                    change += " ⚠"
            else:
                change = "N/A"
            
            line = f"{metric:<40} {base_val:>12} {target_val:>12} {change:>12}"
            lines.append(line)
        
        return lines
    
    def _format_value(self, value: Any) -> str:
        """Форматирование значения"""
        if value is None:
            return "N/A"
        elif isinstance(value, float):
            return f"{value:.2f}"
        elif isinstance(value, int):
            return f"{value:,}"
        else:
            return str(value)[:10]
    
    def _format_comparison_type(self, comp_type: str) -> str:
        """Форматирование типа сравнения"""
        types = {
            'oracle_oracle': 'Oracle AWR ↔ Oracle AWR',
            'postgres_postgres': 'PostgreSQL pg_profile ↔ PostgreSQL pg_profile',
            'cross_platform': 'Oracle AWR ↔ PostgreSQL pg_profile (кросс-платформенное)'
        }
        return types.get(comp_type, comp_type)
    
    def _generate_html_report(self, data: Dict[str, Any]) -> str:
        """Генерация HTML отчета"""
        html = []
        
        html.append("<!DOCTYPE html>")
        html.append("<html lang='ru'>")
        html.append("<head>")
        html.append("  <meta charset='UTF-8'>")
        html.append("  <title>Отчет о сравнении</title>")
        html.append("  <style>")
        html.append(self._get_html_styles())
        html.append("  </style>")
        html.append("</head>")
        html.append("<body>")
        
        # Заголовок
        html.append("  <h1>Отчет о сравнении отчетов о производительности БД</h1>")
        
        # Информация о сравнении
        html.append("  <div class='section'>")
        html.append("    <h2>Информация о сравнении</h2>")
        html.append(f"    <p><strong>Тип сравнения:</strong> {self._format_comparison_type(data['comparison_type'])}</p>")
        
        base_meta = data['base_metadata']
        target_meta = data['target_metadata']
        
        html.append("    <h3>Базовый отчет</h3>")
        html.append(f"    <p>Тип: {base_meta.report_type}</p>")
        html.append(f"    <p>БД: {base_meta.database_name}</p>")
        html.append(f"    <p>Версия: {base_meta.version}</p>")
        
        html.append("    <h3>Целевой отчет</h3>")
        html.append(f"    <p>Тип: {target_meta.report_type}</p>")
        html.append(f"    <p>БД: {target_meta.database_name}</p>")
        html.append(f"    <p>Версия: {target_meta.version}</p>")
        html.append("  </div>")
        
        # Сводка
        summary = data['summary']
        html.append("  <div class='section summary'>")
        html.append("    <h2>Сводка</h2>")
        html.append(f"    <p>Сравнено таблиц: {summary['total_tables']}</p>")
        html.append(f"    <p>Всего метрик: {summary['total_comparisons']}</p>")
        html.append(f"    <p>Критических отклонений: <span class='critical'>{summary['critical_count']}</span></p>")
        html.append(f"    <p>Предупреждений: <span class='warning'>{summary['warning_count']}</span></p>")
        html.append("  </div>")
        
        # Детальное сравнение
        html.append("  <div class='section'>")
        html.append("    <h2>Детальное сравнение</h2>")
        
        for table_comp in data['table_comparisons']:
            html.append(f"    <h3>{table_comp.table_description}</h3>")
            html.append("    <table>")
            html.append("      <thead>")
            html.append("        <tr>")
            html.append("          <th>Метрика</th>")
            html.append("          <th>Базовый</th>")
            html.append("          <th>Целевой</th>")
            html.append("          <th>Изменение</th>")
            html.append("        </tr>")
            html.append("      </thead>")
            html.append("      <tbody>")
            
            for comp in table_comp.comparisons:
                row_class = ""
                if comp.is_critical:
                    row_class = "critical"
                elif comp.is_warning:
                    row_class = "warning"
                
                html.append(f"        <tr class='{row_class}'>")
                html.append(f"          <td>{comp.metric_name}</td>")
                html.append(f"          <td>{self._format_value(comp.base_value)}</td>")
                html.append(f"          <td>{self._format_value(comp.target_value)}</td>")
                
                if comp.percent_change is not None:
                    change_text = f"{comp.percent_change:+.1f}% {comp.get_indicator()}"
                else:
                    change_text = "N/A"
                
                html.append(f"          <td>{change_text}</td>")
                html.append("        </tr>")
            
            html.append("      </tbody>")
            html.append("    </table>")
        
        html.append("  </div>")
        html.append("</body>")
        html.append("</html>")
        
        return "\n".join(html)
    
    def _get_html_styles(self) -> str:
        """CSS стили для HTML отчета"""
        return """
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 20px;
        }
        h3 {
            color: #666;
        }
        .section {
            background-color: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .summary {
            background-color: #e7f3ff;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #007bff;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .critical {
            background-color: #ffebee;
            color: #c62828;
            font-weight: bold;
        }
        .warning {
            background-color: #fff3e0;
            color: #ef6c00;
        }
        """
    
    def _generate_csv_report(self, data: Dict[str, Any]) -> str:
        """Генерация CSV отчета"""
        lines = []
        
        # Заголовок
        lines.append("Таблица,Метрика,Базовый,Целевой,Изменение (%),Статус")
        
        # Данные
        for table_comp in data['table_comparisons']:
            for comp in table_comp.comparisons:
                status = ""
                if comp.is_critical:
                    status = "КРИТИЧЕСКОЕ"
                elif comp.is_warning:
                    status = "ПРЕДУПРЕЖДЕНИЕ"
                else:
                    status = "OK"
                
                change = f"{comp.percent_change:.2f}" if comp.percent_change is not None else "N/A"
                
                line = f"{table_comp.table_description},{comp.metric_name},"
                line += f"{self._format_value(comp.base_value)},{self._format_value(comp.target_value)},"
                line += f"{change},{status}"
                
                lines.append(line)
        
        return "\n".join(lines)
    
    def _generate_json_report(self, data: Dict[str, Any]) -> str:
        """Генерация JSON отчета"""
        # Преобразование объектов в словари
        report_data = {
            'comparison_type': data['comparison_type'],
            'base_metadata': {
                'report_type': data['base_metadata'].report_type,
                'version': data['base_metadata'].version,
                'database_name': data['base_metadata'].database_name,
                'instance_name': data['base_metadata'].instance_name
            },
            'target_metadata': {
                'report_type': data['target_metadata'].report_type,
                'version': data['target_metadata'].version,
                'database_name': data['target_metadata'].database_name,
                'instance_name': data['target_metadata'].instance_name
            },
            'summary': data['summary'],
            'tables': []
        }
        
        for table_comp in data['table_comparisons']:
            table_data = {
                'name': table_comp.table_name,
                'description': table_comp.table_description,
                'comparisons': []
            }
            
            for comp in table_comp.comparisons:
                comp_data = {
                    'metric': comp.metric_name,
                    'base_value': comp.base_value,
                    'target_value': comp.target_value,
                    'absolute_change': comp.absolute_change,
                    'percent_change': comp.percent_change,
                    'is_warning': comp.is_warning,
                    'is_critical': comp.is_critical
                }
                table_data['comparisons'].append(comp_data)
            
            report_data['tables'].append(table_data)
        
        return json.dumps(report_data, ensure_ascii=False, indent=2)
