"""
Парсер для PostgreSQL pg_profile отчетов
"""
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup

from .base_parser import BaseReportParser, ReportMetadata, TableData


class PgProfileParser(BaseReportParser):
    """Парсер для PostgreSQL pg_profile отчетов"""
    
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.soup: Optional[BeautifulSoup] = None
        
    def parse(self) -> bool:
        """Парсинг pg_profile отчета"""
        try:
            content = self._read_file()
            
            # Определение формата (HTML или текстовый)
            if '<html' in content.lower() or '<table' in content.lower():
                self.soup = BeautifulSoup(content, 'lxml')
                return self._parse_html()
            else:
                return self._parse_text()
                
        except Exception as e:
            print(f"Ошибка при парсинге pg_profile отчета: {e}")
            return False
    
    def _parse_html(self) -> bool:
        """Парсинг HTML формата pg_profile"""
        try:
            # Извлечение метаданных
            self.metadata = self.extract_metadata()
            
            # Извлечение основных таблиц
            table_names = [
                'general_statistics',
                'wait_events',
                'database_statistics',
                'queries_statistics',
                'io_statistics',
                'table_statistics',
                'index_statistics'
            ]
            
            for table_name in table_names:
                table_data = self.extract_table(table_name)
                if table_data and not table_data.is_empty():
                    self.tables[table_name] = table_data
            
            return True
            
        except Exception as e:
            print(f"Ошибка при парсинге HTML pg_profile: {e}")
            return False
    
    def _parse_text(self) -> bool:
        """Парсинг текстового формата pg_profile"""
        try:
            content = self._raw_content
            
            # Извлечение метаданных
            self.metadata = self.extract_metadata()
            
            # Парсинг основных секций
            general_stats = self._extract_general_statistics_text(content)
            if general_stats:
                self.tables['general_statistics'] = general_stats
            
            wait_events = self._extract_wait_events_text(content)
            if wait_events:
                self.tables['wait_events'] = wait_events
            
            queries = self._extract_queries_text(content)
            if queries:
                self.tables['queries_statistics'] = queries
            
            return True
            
        except Exception as e:
            print(f"Ошибка при парсинге текстового pg_profile: {e}")
            return False
    
    def extract_metadata(self) -> ReportMetadata:
        """Извлечение метаданных из pg_profile отчета"""
        if self.soup:
            return self._extract_metadata_html()
        else:
            return self._extract_metadata_text()
    
    def _extract_metadata_html(self) -> ReportMetadata:
        """Извлечение метаданных из HTML"""
        db_name = "Unknown"
        instance_name = "Unknown"
        version = "Unknown"
        pg_profile_version = "Unknown"
        start_time = None
        end_time = None
        
        # Поиск информации в заголовке отчета
        for div in self.soup.find_all(['div', 'h1', 'h2']):
            text = div.get_text()
            
            # Поиск версии PostgreSQL
            ver_match = re.search(r'PostgreSQL\s+([\d\.]+)', text)
            if ver_match:
                version = ver_match.group(1)
            
            # Поиск версии pg_profile
            pg_ver_match = re.search(r'pg_profile\s+([\d\.]+)', text)
            if pg_ver_match:
                pg_profile_version = pg_ver_match.group(1)
            
            # Поиск имени БД
            db_match = re.search(r'Database[:\s]+(\w+)', text)
            if db_match:
                db_name = db_match.group(1)
            
            # Поиск имени сервера
            srv_match = re.search(r'Server[:\s]+(\w+)', text)
            if srv_match:
                instance_name = srv_match.group(1)
        
        # Поиск периода отчета
        for table in self.soup.find_all('table'):
            text = table.get_text()
            
            # Поиск времени начала
            start_match = re.search(r'Start time[:\s]+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text)
            if start_match:
                try:
                    start_time = datetime.strptime(start_match.group(1), '%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            # Поиск времени окончания
            end_match = re.search(r'End time[:\s]+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text)
            if end_match:
                try:
                    end_time = datetime.strptime(end_match.group(1), '%Y-%m-%d %H:%M:%S')
                except:
                    pass
        
        duration = None
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds() / 60
        
        return ReportMetadata(
            report_type='postgresql_pg_profile',
            version=f"PostgreSQL {version}, pg_profile {pg_profile_version}",
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
        
        # Поиск версии PostgreSQL
        ver_match = re.search(r'PostgreSQL\s+([\d\.]+)', content)
        if ver_match:
            version = ver_match.group(1)
        
        # Поиск имени БД
        db_match = re.search(r'Database[:\s]+(\w+)', content)
        if db_match:
            db_name = db_match.group(1)
        
        # Поиск имени сервера
        srv_match = re.search(r'Server[:\s]+(\w+)', content)
        if srv_match:
            instance_name = srv_match.group(1)
        
        return ReportMetadata(
            report_type='postgresql_pg_profile',
            version=version,
            database_name=db_name,
            instance_name=instance_name,
            start_time=None,
            end_time=None,
            duration_minutes=None
        )
    
    def extract_table(self, table_name: str) -> Optional[TableData]:
        """Извлечение конкретной таблицы из pg_profile отчета"""
        if self.soup:
            return self._extract_table_html(table_name)
        else:
            return self._extract_table_text(table_name)
    
    def _extract_table_html(self, table_name: str) -> Optional[TableData]:
        """Извлечение таблицы из HTML"""
        # Маппинг названий таблиц на заголовки в отчете
        table_headers = {
            'general_statistics': 'Cluster statistics',
            'wait_events': 'Wait event.*statistics',
            'database_statistics': 'Database statistics',
            'queries_statistics': 'Top.*SQL.*by.*elapsed',
            'io_statistics': 'I/O.*statistics',
            'table_statistics': 'Top.*tables',
            'index_statistics': 'Top.*indexes'
        }
        
        header_pattern = table_headers.get(table_name)
        if not header_pattern:
            return None
        
        # Поиск таблицы по заголовку
        for heading in self.soup.find_all(['h2', 'h3', 'h4', 'a']):
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
        if table_name == 'general_statistics':
            return self._extract_general_statistics_text(self._raw_content)
        elif table_name == 'wait_events':
            return self._extract_wait_events_text(self._raw_content)
        elif table_name == 'queries_statistics':
            return self._extract_queries_text(self._raw_content)
        
        return None
    
    def _extract_general_statistics_text(self, content: str) -> Optional[TableData]:
        """Извлечение общей статистики из текста"""
        match = re.search(r'Cluster statistics\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL)
        if not match:
            return None
        
        section = match.group(1)
        headers = ['Metric', 'Value']
        rows = []
        
        for line in section.split('\n'):
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    rows.append({
                        'Metric': parts[0].strip(),
                        'Value': self._normalize_value(parts[1].strip())
                    })
        
        return TableData(
            name='general_statistics',
            headers=headers,
            rows=rows,
            metadata={}
        )
    
    def _extract_wait_events_text(self, content: str) -> Optional[TableData]:
        """Извлечение событий ожидания из текста"""
        match = re.search(r'Wait event.*statistics\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
        if not match:
            return None
        
        section = match.group(1)
        headers = ['Event', 'Count', 'Time (ms)', '% Total']
        rows = []
        
        for line in section.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    rows.append({
                        'Event': ' '.join(parts[:-3]),
                        'Count': self._normalize_value(parts[-3]),
                        'Time (ms)': self._normalize_value(parts[-2]),
                        '% Total': self._normalize_value(parts[-1])
                    })
        
        return TableData(
            name='wait_events',
            headers=headers,
            rows=rows,
            metadata={}
        )
    
    def _extract_queries_text(self, content: str) -> Optional[TableData]:
        """Извлечение статистики запросов из текста"""
        match = re.search(r'Top.*SQL.*by.*elapsed\s*\n(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
        if not match:
            return None
        
        section = match.group(1)
        headers = ['Query ID', 'Calls', 'Total time', 'Mean time']
        rows = []
        
        for line in section.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    rows.append({
                        'Query ID': parts[0],
                        'Calls': self._normalize_value(parts[1]),
                        'Total time': self._normalize_value(parts[2]),
                        'Mean time': self._normalize_value(parts[3])
                    })
        
        return TableData(
            name='queries_statistics',
            headers=headers,
            rows=rows,
            metadata={}
        )
