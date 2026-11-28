"""Read-only checks run inside the real base-only receiving interpreter."""
import inspect


def ocr_absence():
    import os
    from pathlib import Path
    import shutil
    import sys
    variables = {name: os.environ.get(name) for name in ('TESSDATA_PREFIX', 'TESSDATA_DIR',
        'TESSERACT_CMD', 'TESSERACT_BINARY', 'SMM_008_OCR_EXECUTABLE', 'SMM_008_OCR_DATA')}
    engines = {Path(name) for name in ('/usr/bin/tesseract', '/usr/local/bin/tesseract', '/opt/homebrew/bin/tesseract')}
    data = {Path(name) for name in ('/usr/share/tesseract-ocr/5/tessdata', '/usr/share/tessdata',
                                  '/usr/local/share/tessdata', '/opt/homebrew/share/tessdata')}
    for variable in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
        if value := os.environ.get(variable):
            engines.add(Path(value) / 'Tesseract-OCR/tesseract.exe')
            data.add(Path(value) / 'Tesseract-OCR/tessdata')
    for variable in ('ProgramData', 'ChocolateyInstall'):
        if value := os.environ.get(variable):
            data.add(Path(value) / 'chocolatey/lib/tesseract/tools/tessdata')
            data.add(Path(value) / 'lib/tesseract/tools/tessdata')
    if engine := shutil.which('tesseract'):
        engines.add(Path(engine))
    present, errors = [], []
    for path in sorted(engines):
        try:
            if path.is_file():
                present.append({'kind': 'engine', 'path': str(path)})
        except OSError as error:
            errors.append({'path': str(path), 'error': type(error).__name__})
    for path in sorted(data):
        try:
            if path.is_dir():
                present.extend({'kind': 'language-data', 'path': str(p)} for p in path.glob('*.traineddata') if p.is_file())
        except OSError as error:
            errors.append({'path': str(path), 'error': type(error).__name__})
    # No-follow traversal: neither a venv base-interpreter link nor a junction
    # is evidence that those external directories were inspected.
    for directory, names, files in os.walk(sys.prefix, followlinks=False,
            onerror=lambda error: errors.append({'path': error.filename, 'error': type(error).__name__})):
        parent = Path(directory)
        names[:] = [name for name in names if not (parent / name).is_symlink()
                    and not getattr((parent / name).lstat(), 'st_file_attributes', 0) & 0x400]
        for name in files:
            if name.lower() in {'tesseract', 'tesseract.exe'} or name.lower().endswith('.traineddata'):
                present.append({'kind': 'product-prefix-component', 'path': str(parent / name)})
    return {'status': 'absent' if not present and not errors and not any(variables.values()) else 'present_or_not_proven',
            'python': sys.executable, 'prefix': sys.prefix, 'isolated': sys.flags.isolated,
            'path': os.environ.get('PATH'), 'ocr_environment': variables,
            'checked_engine_locations': sorted(map(str, engines)), 'checked_language_directories': sorted(map(str, data)),
            'whole_product_prefix_no_follow': True, 'present': present, 'observation_errors': errors,
            'scope': 'Actual product prefix, product PATH, explicit OCR settings and normal OS component locations; no OCR or dependency install performed.'}


OCR_ABSENCE_SOURCE = inspect.getsource(ocr_absence)
