import os

def collect_python_files():
    current_dir = os.getcwd()
    output_file = os.path.join(current_dir, 'code.txt')
    
    # Удаляем старый code.txt если существует
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f'Удалён старый файл: {output_file}')
    
    # Папки, которые нужно пропускать
    skip_dirs = {'venv', '.venv', 'env', '.env', '__pycache__', '.git'}
    
    python_files = []
    
    # Обходим все папки и подпапки
    for root, dirs, files in os.walk(current_dir):
        # Исключаем ненужные папки из обхода
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for filename in files:
            if filename.endswith('.py'):
                full_path = os.path.join(root, filename)
                # Пропускаем сам скрипт
                if os.path.abspath(full_path) == os.path.abspath(__file__):
                    continue
                python_files.append(full_path)
    
    # Сортируем для удобства
    python_files.sort()
    
    with open(output_file, 'w', encoding='utf-8') as out:
        for i, filepath in enumerate(python_files):
            out.write('#' * 80 + '\n')
            out.write(f'# Файл: {filepath}\n')
            out.write('#' * 80 + '\n\n')
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                out.write(content)
            except UnicodeDecodeError:
                try:
                    with open(filepath, 'r', encoding='cp1251') as f:
                        content = f.read()
                    out.write(content)
                except Exception as e:
                    out.write(f'# Ошибка чтения файла: {e}\n')
            except Exception as e:
                out.write(f'# Ошибка чтения файла: {e}\n')
            
            if i < len(python_files) - 1:
                out.write('\n\n\n')
    
    print(f'\nГотово! Найдено Python-файлов: {len(python_files)}')
    print(f'Результат сохранён в: {output_file}')
    
    if python_files:
        print('\nСписок найденных файлов:')
        for filepath in python_files:
            print(f'  {filepath}')
    else:
        print('\nPython-файлы не найдены.')

if __name__ == '__main__':
    collect_python_files()