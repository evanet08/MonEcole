#!/usr/bin/env python3
"""
Migration script: Convert standalone MonEcole templates to extend base_monecole.html
Run this on the production server.
"""
import os
import re
import shutil

TEMPLATE_DIR = '/var/www/vhosts/monecole.pro/httpdocs/monecole_pro/MonEcole_app/templates'
BACKUP_DIR = '/var/www/vhosts/monecole.pro/httpdocs/monecole_pro/MonEcole_app/templates_backup_migration'

# Templates to migrate with their active_page value and title
TEMPLATES = {
    'inscription/index_inscription.html': {'active_page': 'inscription', 'title': 'Inscription'},
    'evaluation/index_evaluation.html': {'active_page': 'evaluation', 'title': 'Évaluation'},
    'enseignement/index_enseignement.html': {'active_page': 'enseignement', 'title': 'Enseignement'},
    'parametrage/index_parametrage.html': {'active_page': 'parametrage', 'title': 'Paramétrage'},
    'recouvrement/index_recouvrement.html': {'active_page': 'recouvrement', 'title': 'Recouvrement'},
    'library/index_library.html': {'active_page': 'library', 'title': 'Bibliothèque'},
    'suivi/index_suivi.html': {'active_page': 'suivi', 'title': 'Suivi'},
    'archives/index_archives.html': {'active_page': 'archives', 'title': 'Archives'},
}


def extract_styles(content):
    """Extract all <style> blocks from the HTML"""
    styles = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    return '\n'.join(f'<style>\n{s.strip()}\n</style>' for s in styles if s.strip())


def extract_scripts(content):
    """Extract all inline <script> blocks (not external CDN ones handled by base)"""
    scripts = []
    # Match inline scripts (with content, not just src)
    for match in re.finditer(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', content, re.DOTALL):
        script_content = match.group(1).strip()
        if script_content:
            scripts.append(f'<script>\n{script_content}\n</script>')
    
    # Also keep external scripts that are NOT already in base (bootstrap, font-awesome, google fonts)
    base_externals = [
        'bootstrap', 'font-awesome', 'cdnjs.cloudflare.com/ajax/libs/font-awesome',
        'fonts.googleapis.com', 'fonts.gstatic.com'
    ]
    for match in re.finditer(r'<script[^>]*src=["\']([^"\']+)["\'][^>]*>\s*</script>', content):
        src = match.group(1)
        if not any(ext in src for ext in base_externals):
            scripts.append(match.group(0))
    
    return '\n\n'.join(scripts)


def extract_body_content(content):
    """Extract the main page content from the body, excluding sidebars, headers, footers"""
    # Remove everything before <body
    body_match = re.search(r'<body[^>]*>(.*)</body>', content, re.DOTALL)
    if not body_match:
        return ''
    
    body = body_match.group(1)
    
    # Remove include tags for partials that are now in base
    partials_to_remove = [
        r'{%\s*include\s+["\']partials/_foot_bar\.html["\']\s*%}',
        r'{%\s*include\s+["\']partials/_profile_bar\.html["\']\s*%}',
        r'{%\s*include\s+["\']partials/title_logo\.html["\']\s*%}',
        r'{%\s*include\s+["\']partials/log_out_button\.html["\']\s*%}',
        r'{%\s*include\s+["\']partials/url_deconnect\.html["\']\s*%}',
        r'{%\s*include\s+["\']partials/url_module\.html["\']\s*%}',
        r'{%\s*include\s+["\']inscription/side_bar\.html["\']\s*%}',
        r'{%\s*include\s+["\']library/sidebar_library\.html["\']\s*%}',
        r'{%\s*include\s+["\']library/script_side\.html["\']\s*%}',
        # direction sidebar
        r'{%\s*include\s+["\']direction_page/_sidebar_direct\.html["\']\s*%}',
    ]
    for pattern in partials_to_remove:
        body = re.sub(pattern, '', body)
    
    # Remove inline <script> tags (they go to page_js block)
    body = re.sub(r'<script(?![^>]*src=)[^>]*>.*?</script>', '', body, flags=re.DOTALL)
    
    # Remove external script tags that aren't in base
    base_externals = [
        'bootstrap', 'font-awesome', 'cdnjs.cloudflare.com/ajax/libs/font-awesome',
        'fonts.googleapis.com', 'fonts.gstatic.com'
    ]
    def should_remove_script(match):
        src = match.group(1) if match.group(1) else ''
        return any(ext in src for ext in base_externals)
    
    body = re.sub(r'<script[^>]*src=["\']([^"\']+)["\'][^>]*>\s*</script>', 
                  lambda m: '' if should_remove_script(m) else m.group(0), body)
    
    # Remove <style> tags (they go to page_css block)
    body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL)
    
    # Clean up excessive blank lines
    body = re.sub(r'\n{3,}', '\n\n', body)
    
    return body.strip()


def migrate_template(rel_path, config):
    """Migrate a single template to extend base_monecole.html"""
    full_path = os.path.join(TEMPLATE_DIR, rel_path)
    
    if not os.path.exists(full_path):
        print(f'  SKIP (not found): {rel_path}')
        return False
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already migrated
    if "extends 'base_monecole.html'" in content or 'extends "base_monecole.html"' in content:
        print(f'  SKIP (already migrated): {rel_path}')
        return False
    
    # Backup
    backup_path = os.path.join(BACKUP_DIR, rel_path)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(full_path, backup_path)
    print(f'  Backed up: {rel_path}')
    
    # Extract parts
    styles = extract_styles(content)
    scripts = extract_scripts(content)
    body_content = extract_body_content(content)
    
    # Check for {% load %} tags
    loads = re.findall(r'{%\s*load\s+\w+\s*%}', content)
    loads_str = '\n'.join(sorted(set(loads)))
    
    # Build new template
    new_content = f"""{{% extends 'base_monecole.html' %}}
{loads_str}

{{% block title %}}{config['title']}{{% endblock %}}

{{% block page_css %}}
{styles}
{{% endblock %}}

{{% block page_content %}}
{body_content}
{{% endblock %}}

{{% block page_js %}}
{scripts}
{{% endblock %}}
"""
    
    # Clean up empty blocks
    new_content = re.sub(r'{%\s*block\s+page_css\s*%}\s*\n\s*\n{%\s*endblock\s*%}', 
                         '{% block page_css %}{% endblock %}', new_content)
    new_content = re.sub(r'{%\s*block\s+page_js\s*%}\s*\n\s*\n{%\s*endblock\s*%}', 
                         '{% block page_js %}{% endblock %}', new_content)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f'  MIGRATED: {rel_path} ({len(content)} -> {len(new_content)} bytes)')
    return True


def main():
    print('=' * 60)
    print('MonEcole Template Migration to base_monecole.html')
    print('=' * 60)
    
    # Create backup dir
    os.makedirs(BACKUP_DIR, exist_ok=True)
    print(f'\nBackup directory: {BACKUP_DIR}\n')
    
    migrated = 0
    for rel_path, config in TEMPLATES.items():
        print(f'\nProcessing: {rel_path}')
        if migrate_template(rel_path, config):
            migrated += 1
    
    print(f'\n{"=" * 60}')
    print(f'Migration complete: {migrated}/{len(TEMPLATES)} templates migrated')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
