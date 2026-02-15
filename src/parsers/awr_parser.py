"""
Парсер для Oracle AWR отчетов
"""
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup

from .base_parser import BaseReportParser, ReportMetadata, TableData


class AWRParser(BaseReportParser):
    """Парсер для Oracle AWR отчетов"""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.soup: Optional[BeautifulSoup] = None
        
    def parse(self) -> bool:
        """Парсинг AWR отчета"""
        try:
            content = self._read_file()
            
            # Определение формата (HTML или текстовый)
            if '<html' in content.lower() or '<table' in content.lower():
                self.soup = BeautifulSoup(content, 'lxml')
                return self._parse_html()
            else:
                return self._parse_text()
                
        except Exception as e:
            print(f"Ошибка при парсинге AWR отчета: {e}")
            return False
    
    def _parse_html(self) -> bool:
        """Парсинг HTML формата AWR"""
        try:
            # Извлечение метаданных
            self.metadata = self.extract_metadata()
            
            # Извлечение основных таблиц
            table_names = [
                'load_profile',
                'instance_efficiency',
                'top_sql_elapsed',
                'top_sql_cpu',
                'wait_events',
                'io_statistics',
                'time_model_statistics'
            ]
            
            for table_name in table_names:
                table_data = self.extract_table(table_name)
                if table_data and not table_data.is_empty():
                    self.tables[table_name] = table_data
            
            return True
            
        except Exception as e:
            print(f"Ошибка при парсинге HTML AWR: {e}")
            return False
    
    def _parse_text(self) -> bool:
        """Парсинг текстового формата AWR"""
        try:
            content = self._raw_content
            
            # Извлечение метаданных
            self.metadata = self.extract_metadata()
            
            # Парсинг Load Profile
            load_profile = self._extract_load_profile_text(content)
            if load_profile:
                self.tables['load_profile'] = load_profile
            
            # Парсинг Top SQL
            top_sql = self._extract_top_sql_text(content)
            if top_sql:
                self.tables['top_sql_elapsed'] = top_sql
            
            # Парсинг Wait Events
            wait_events = self._extract_wait_events_text(content)
            if wait_events:
                self.tables['wait_events'] = wait_events
            
            return True
            
        except Exception as e:
            print(f"Ошибка при парсинге текстового AWR: {e}")
            return False
    
    def extract_metadata(self) -> ReportMetadata:
        """Извлечение метаданных из AWR отчета"""
        if self.soup:
            return self._extract_metadata_html()
        else:
            return self._extract_metadata_text()
    
    def _extract_metadata_html(self) -> ReportMetadata:
        """Извлечение метаданных из HTML"""
        # Поиск информации о БД и экземпляре
        db_name = "Unknown"
        instance_name = "Unknown"
        version = "Unknown"
        start_time = None
        end_time = None
        
        # Поиск в таблицах с метаданными
        for table in self.soup.find_all('table'):
            text = table.get_text()
            
            # Поиск имени БД
            db_match = re.search(r'DB Name[:\s]+(\w+)', text)
            if db_match:
                db_name = db_match.group(1)
            
            # Поиск имени экземпляра
            inst_match = re.search(r'Instance[:\s]+(\w+)', text)
            if inst_match:
                instance_name = inst_match.group(1)
            
            # Поиск версии
            ver_match = re.search(r'Release[:\s]+([\d\.]+)', text)
            if ver_match:
                version = ver_match.group(1)
            
            # Поиск времени начала и конца
            time_match = re.search(r'Begin Snap[:\s]+.*?(\d{2}-\w{3}-\d{2,4}\s+\d{2}:\d{2})', text)
            if time_match:
                try:
                    start_time = datetime.strptime(time_match.group(1), '%d-%b-%y %H:%M')
                except:
                    pass
            
            time_match = re.search(r'End Snap[:\s]+.*?(\d{2}-\w{3}-\d{2,4}\s+\d{2}:\d{2})', text)
            if time_match:
                try:
                    end_time = datetime.strptime(time_match.group(1), '%d-%b-%y %H:%M')
                except:
                    pass
        
        duration = None
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds() / 60
        
        return ReportMetadata(
            report_type='oracle_awr',
            version=version,
            database_name=db_name,
            instance_name=instance_name,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration
        )
    
    def _extract_metadata_text(self) -> ReportMetadata:
        """Извлечение метаданных из текстового формата"""
        content = self._raw_content
        
        db_name = "Unknown"
        instance_name = "Unknown"
        version = "Unknown"
        
        # Поиск имени БД
        db_match = re.search(r'DB Name[:\s]+(\w+)', content)
        if db_match:
            db_name = db_match.group(1)
        
        # Поиск имени экземпляра
        inst_match = re.search(r'Instance[:\s]+(\w+)', content)
        if inst_match:
            instance_name = inst_match.group(1)
        
        # Поиск версии
        ver_match = re.search(r'Release[:\s]+([\d\.]+)', content)
        if ver_match:
            version = ver_match.group(1)
        
        return ReportMetadata(
            report_type='oracle_awr',
            version=version,
            database_name=db_name,
            instance_name=instance_name,
            start_time=None,
            end_time=None,
            duration_minutes=None
        )
    
    def extract_table(self, table_name: str) -> Optional[TableData]:
        """Извлечение конкретной таблицы из AWR отчета"""
        if self.soup:
            return self._extract_table_html(table_name)
        else:
            return self._extract_table_text(table_name)
    
    def _extract_table_html(self, table_name: str) -> Optional[TableData]:
        """Извлечение таблицы из HTML"""
        # Маппинг названий таблиц на заголовки в отчете
        table_headers = {
            'load_profile': 'Load Profile',
            'instance_efficiency': 'Instance Efficiency',
            'top_sql_elapsed': 'SQL ordered by Elapsed Time',
            'top_sql_cpu': 'SQL ordered by CPU Time',
            'wait_events': 'Top.*Wait Events',
            'io_statistics': 'IOStat by',
            'time_model_statistics': 'Time Model Statistics'
        }
        
        header_pattern = table_headers.get(table_name)
        if not header_pattern:
            return None
        
        # Поиск таблицы по заголовку
        for heading in self.soup.find_all(['h2', 'h3', 'a']):
            if re.search(header_pattern, heading.get_text(), re.IGNORECASE):
                # Найти следующую таблицу после заголовка
                table = heading.find_next('table')
                if table:
                    return self._parse_html_table(table, table_name)
        
        return None
    
    def _parse_html_table(self, table, table_name: str) -> TableData:
        """Парсинг HTML таблицы"""
        headers = []
        rows = []
        
        # Извлечение заголовков
        header_row = table.find('tr')
        if header_row:
            headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
        
        # Извлечение строк данных
        for tr in table.find_all('tr')[1:]:  # Пропускаем заголовок
            cells = tr.find_all('td')
            if cells and len(cells) == len(headers):
                row_data = {}
                for i, cell in enumerate(cells):
                    value = cell.get_text().strip()
                    row_data[headers[i]] = self._normalize_value(value)
                rows.append(row_data)
        
        return TableData(
            name=table_name,
            headers=headers,
            rows=rows,
            metadata={}
        )
    
    def _extract_table_text(self, table_name: str) -> Optional[TableData]:
        """Извлечение таблицы из текстового формата"""
        # Реализация для текстового формата
        if table_name == 'load_profile':
            return self._extract_load_profile_text(self._raw_content)
        elif table_name == 'top_sql_elapsed':
            return self._extract_top_sql_text(self._raw_content)
        elif table_name == 'wait_events':
            return self._extract_wait_events_text(self._raw_content)
        
        return None
    
    def _extract_load_profile_text(self, content: str) -> Optional[TableData]:
        """Извлечение Load Profile из текста"""
        # Поиск секции Load Profile
        match = re.search(r'Load Profile\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL)
        if not match:
            return None
        
        section = match.group(1)
        headers = ['Metric', 'Per Second', 'Per Transaction']
        rows = []
        
        # Парсинг строк метрик
        for line in section.split('\n'):
            if ':' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    metric = parts[0].strip()
                    values = parts[1].strip().split()
                    if len(values) >= 2:
                        rows.append({
                            'Metric': metric,
                            'Per Second': self._normalize_value(values[0]),
                            'Per Transaction': self._normalize_value(values[1]) if len(values) > 1 else None
                        })
        
        return TableData(
            name='load_profile',
            headers=headers,
            rows=rows,
            metadata={}
        )
    
    def _extract_top_sql_text(self, content: str) -> Optional[TableData]:
        """Извлечение Top SQL из текста"""
        match = re.search(r'SQL ordered by Elapsed Time\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL)
        if not match:
            return None
        
        section = match.group(1)
        headers = ['SQL ID', 'Elapsed Time', 'CPU Time', 'Executions']
        rows = []
        
        # Простой парсинг (требует доработки под конкретный формат)
        for line in section.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    rows.append({
                        'SQL ID': parts[0],
                        'Elapsed Time': self._normalize_value(parts[1]),
                        'CPU Time': self._normalize_value(parts[2]),
                        'Executions': self._normalize_value(parts[3])
                    })
        
        return TableData(
            name='top_sql_elapsed',
            headers=headers,
            rows=rows,
            metadata={}
        )
    
    def _extract_wait_events_text(self, content: str) -> Optional[TableData]:
        """Извлечение Wait Events из текста"""
        match = re.search(r'Top.*Wait Events\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL)
        if not match:
            return None
        
        section = match.group(1)
        headers = ['Event', 'Waits', 'Time(s)', '% DB Time']
        rows = []
        
        for line in section.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    rows.append({
                        'Event': ' '.join(parts[:-3]),
                        'Waits': self._normalize_value(parts[-3]),
                        'Time(s)': self._normalize_value(parts[-2]),
                        '% DB Time': self._normalize_value(parts[-1])
                    })
        
        return TableData(
            name='wait_events',
            headers=headers,
            rows=rows,
            metadata={}
        )
