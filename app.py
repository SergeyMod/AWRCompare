"""
Веб-приложение для сравнения AWR и pg_profile отчетов
"""
import os
import uuid
import tempfile
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename

from src.parsers import AWRParser, PgProfileParser
from src.comparison import ComparisonEngine
from src.report_generator import ReportGenerator
from src.utils import config_loader

app = Flask(__name__)
app.secret_key = 'awr-pgprofile-comparison-secret-key'

# Настройки загрузки файлов
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'html', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max

# Глобальные переменные для хранения состояния сессии
comparison_results = {}


def allowed_file(filename):
    """Проверка расширения файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_parser_for_file(filepath):
    """Создание парсера на основе содержимого файла"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read(5000)
    
    if 'AWR' in content or 'Automatic Workload Repository' in content:
        return AWRParser(filepath)
    elif 'pg_profile' in content or 'PostgreSQL' in content:
        return PgProfileParser(filepath)
    else:
        # По умолчанию пробуем AWR
        return AWRParser(filepath)


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    """Загрузка и парсинг файлов отчетов"""
    session_id = str(uuid.uuid4())
    
    # Проверка файлов
    if 'base_file' not in request.files or 'target_file' not in request.files:
        flash('Пожалуйста, выберите оба файла отчетов', 'error')
        return redirect(url_for('index'))
    
    base_file = request.files['base_file']
    target_file = request.files['target_file']
    
    if base_file.filename == '' or target_file.filename == '':
        flash('Выберите файлы для загрузки', 'error')
        return redirect(url_for('index'))
    
    if not (allowed_file(base_file.filename) and allowed_file(target_file.filename)):
        flash('Неподдерживаемый формат файла. Используйте .html или .txt', 'error')
        return redirect(url_for('index'))
    
    try:
        # Сохранение файлов
        base_filename = secure_filename(base_file.filename)
        target_filename = secure_filename(target_file.filename)
        
        base_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_base_{base_filename}")
        target_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_target_{target_filename}")
        
        base_file.save(base_filepath)
        target_file.save(target_filepath)
        
        # Парсинг отчетов
        base_parser = get_parser_for_file(base_filepath)
        target_parser = get_parser_for_file(target_filepath)
        
        if not base_parser.parse():
            flash('Не удалось распарсить базовый отчет', 'error')
            return redirect(url_for('index'))
        
        if not target_parser.parse():
            flash('Не удалось распарсить целевой отчет', 'error')
            return redirect(url_for('index'))
        
        # Сохранение парсеров в сессии
        comparison_results[session_id] = {
            'base_parser': base_parser,
            'target_parser': target_parser,
            'base_filename': base_filename,
            'target_filename': target_filename,
            'base_filepath': base_filepath,
            'target_filepath': target_filepath
        }
        
        # Определение доступных таблиц
        base_tables = set(base_parser.get_available_tables())
        target_tables = set(target_parser.get_available_tables())
        common_tables = sorted(base_tables & target_tables)
        
        return render_template('select_tables.html', 
                            session_id=session_id,
                            base_metadata=base_parser.metadata,
                            target_metadata=target_parser.metadata,
                            available_tables=common_tables,
                            base_filename=base_filename,
                            target_filename=target_filename)
    
    except Exception as e:
        flash(f'Ошибка при загрузке отчетов: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/compare', methods=['POST'])
def compare():
    """Выполнение сравнения отчетов"""
    session_id = request.form.get('session_id')
    selected_tables = request.form.getlist('tables')
    export_format = request.form.get('export_format', 'html')
    
    if session_id not in comparison_results:
        flash('Сессия истекла. Пожалуйста, загрузите отчеты заново', 'error')
        return redirect(url_for('index'))
    
    if not selected_tables:
        flash('Выберите хотя бы одну таблицу для сравнения', 'error')
        return redirect(url_for('index'))
    
    try:
        session_data = comparison_results[session_id]
        base_parser = session_data['base_parser']
        target_parser = session_data['target_parser']
        
        # Выполнение сравнения
        engine = ComparisonEngine()
        results = engine.compare_reports(base_parser, target_parser, selected_tables)
        
        # Генерация отчета
        generator = ReportGenerator()
        report_content = generator.generate_report(results, output_format=export_format)
        
        # Сохранение результата
        extension = export_format
        result_filename = f"comparison_report_{session_id[:8]}.{extension}"
        result_filepath = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)
        
        with open(result_filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # Подготовка данных для отображения
        comparison_data = {
            'comparison_type': results['comparison_type'],
            'base_metadata': results['base_metadata'],
            'target_metadata': results['target_metadata'],
            'table_comparisons': results['table_comparisons'],
            'summary': results['summary'],
            'thresholds': results['thresholds'],
            'format': export_format,
            'download_url': url_for('download_file', filename=result_filename)
        }
        
        return render_template('results.html', **comparison_data)
    
    except Exception as e:
        flash(f'Ошибка при сравнении: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/download/<filename>')
def download_file(filename):
    """Скачивание файла отчета"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        flash('Файл не найден', 'error')
        return redirect(url_for('index'))


@app.route('/clear/<session_id>')
def clear_session(session_id):
    """Очистка сессии"""
    if session_id in comparison_results:
        session_data = comparison_results[session_id]
        
        # Удаление временных файлов
        for key in ['base_filepath', 'target_filepath']:
            if key in session_data:
                filepath = session_data[key]
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except:
                        pass
        
        # Удаление результатов сравнения
        upload_folder = app.config['UPLOAD_FOLDER']
        for f in os.listdir(upload_folder):
            if f.startswith('comparison_report_') and session_id[:8] in f:
                try:
                    os.remove(os.path.join(upload_folder, f))
                except:
                    pass
        
        del comparison_results[session_id]
    
    return redirect(url_for('index'))


if __name__ == '__main__':
    # Создание директории для шаблонов
    os.makedirs('templates', exist_ok=True)
    
    print("=" * 60)
    print("Запуск веб-приложения AWR/pg_profile Comparison")
    print("=" * 60)
    print("Откройте в браузере: http://127.0.0.1:5000")
    print("=" * 60)
    
    app.run(debug=True, host='127.0.0.1', port=5000)
