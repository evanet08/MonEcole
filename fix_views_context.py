#!/usr/bin/env python3
"""
Fix views to pass active_page context variable for sidebar highlighting.
Run this on the production server.
"""
import re

VIEW_FILE = '/var/www/vhosts/monecole.pro/httpdocs/monecole_pro/MonEcole_app/views/home/home.py'

# Map function name -> active_page value
ACTIVE_PAGE_MAP = {
    'redirect_to_parametrage': 'parametrage',
    'redirect_to_evaluation': 'evaluation',
    'redirect_to_inscription': 'inscription',
    'redirect_to_enseignement': 'enseignement',
    'redirect_to_recouvrement': 'recouvrement',
    'redirect_to_achive': 'archives',
    'redirect_to_library': 'library',
    'redirect_to_suivi_eleve': 'suivi',
}

def fix_views():
    with open(VIEW_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    for func_name, active_page in ACTIVE_PAGE_MAP.items():
        # Pattern: find render calls inside each function and add active_page
        # Look for the context dict closing
        # We need to add "active_page": "xxx" to each render call's context
        
        # Strategy: find the function block, then find the render(...) call within it
        # and add active_page to the context dict
        
        # Match patterns like: "last_name": user_modules['last_name']}
        # and add "active_page": "xxx" before the closing }
        
        # Find the function definition
        func_pattern = rf'def {func_name}\(request\):(.*?)(?=\n(?:@|def |\Z))'
        func_match = re.search(func_pattern, content, re.DOTALL)
        
        if not func_match:
            print(f'  WARNING: Function {func_name} not found')
            continue
        
        func_body = func_match.group(0)
        
        # Check if active_page already present
        if 'active_page' in func_body:
            print(f'  SKIP (already has active_page): {func_name}')
            continue
        
        # Find the last } before the closing ) of render
        # Add active_page before it
        # Pattern: "last_name": user_modules['last_name']} or similar ending
        new_func_body = re.sub(
            r'("last_name"\s*:\s*user_modules\[\'last_name\'\]\s*)(})',
            rf'\1,\n                    "active_page": "{active_page}"\2',
            func_body
        )
        
        if new_func_body == func_body:
            # Try alternate pattern with trailing comma or whitespace differences
            new_func_body = re.sub(
                r'("last_name"\s*:\s*user_modules\[\'last_name\'\]\s*,?\s*\n?\s*)(})',
                rf'"last_name": user_modules[\'last_name\'],\n                    "active_page": "{active_page}"\2',
                func_body
            )
        
        if new_func_body != func_body:
            content = content.replace(func_body, new_func_body)
            print(f'  FIXED: {func_name} -> active_page="{active_page}"')
        else:
            print(f'  WARNING: Could not modify {func_name} - manual fix needed')
    
    if content != original:
        # Backup
        with open(VIEW_FILE + '.bak', 'w', encoding='utf-8') as f:
            f.write(original)
        print(f'\n  Backup saved: {VIEW_FILE}.bak')
        
        with open(VIEW_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  Updated: {VIEW_FILE}')
    else:
        print('\n  No changes needed.')

if __name__ == '__main__':
    print('Fixing views context...')
    fix_views()
    print('Done!')
