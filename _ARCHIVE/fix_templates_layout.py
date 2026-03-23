#!/usr/bin/env python3
"""
Fix all module templates: remove old sidebar divs and main-content wrappers
that conflict with base_monecole.html layout.
"""
import re
import os

TEMPLATES_DIR = '/home/drevaristen/Desktop/MonEcole/MonEcole_app/templates'

def fix_template(filepath):
    """Remove old sidebar divs, mobile-nav-toggle, ep-bg-animation, 
    main-content wrapper, and bottom-navbar from a template."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Remove <div class="ep-bg-animation">...</div>
    content = re.sub(
        r'<div class="ep-bg-animation">.*?</div>\s*</div>\s*',
        '', content, flags=re.DOTALL
    )
    
    # Remove mobile-nav-toggle div
    content = re.sub(
        r'\s*<!\-\- Mobile Toggle Button \-\->.*?</div>\s*',
        '\n', content, flags=re.DOTALL
    )
    content = re.sub(
        r'\s*<div class="mobile-nav-toggle">.*?</div>\s*',
        '\n', content, flags=re.DOTALL
    )
    
    # Remove sidebar includes
    content = re.sub(
        r"\s*{%\s*include\s+'enseignement/_sidebar_ensgmnt\.html'\s*%}\s*",
        '\n', content
    )
    content = re.sub(
        r"\s*{%\s*include\s+'recouvrement/_sidebar_direct\.html'\s*%}\s*",
        '\n', content
    )
    content = re.sub(
        r"\s*{%\s*include\s+'inscription/side_bar\.html'\s*%}\s*",
        '\n', content
    )
    
    # Remove inline sidebar divs (with all their content)
    # Pattern: <div class="sidebar">...content...</div> followed by comments
    content = re.sub(
        r'\s*<!\-\-\s*=+Sidebar.*?\-\->\s*<div class="sidebar">.*?</div>\s*',
        '\n', content, flags=re.DOTALL
    )
    # Also catch standalone sidebar divs
    content = re.sub(
        r'\s*<div class="sidebar">\s*<div class="menu">.*?</div>\s*</div>\s*',
        '\n', content, flags=re.DOTALL
    )
    # Catch empty sidebars
    content = re.sub(
        r'\s*<div class="sidebar">\s*</div>\s*',
        '\n', content, flags=re.DOTALL
    )
    
    # Remove bottom navbar comments/includes
    content = re.sub(
        r'\s*<!\-\-\s*=+Bottom Navigation.*?\-\->\s*',
        '\n', content
    )
    
    # Remove <div class="main-content"> opening and its closing </div>
    # This is tricky - we need to remove the wrapper but keep content
    # Strategy: remove the opening tag and track to remove one closing div
    if '<div class="main-content">' in content:
        # Remove the opening tag and its comment
        content = re.sub(
            r'\s*<!\-\-\s*Main Content\s*\-\->\s*<div class="main-content">\s*',
            '\n', content
        )
        # Also try without comment
        content = content.replace('<div class="main-content">', '')
        
        # Now we need to remove ONE extra closing </div> before {% endblock %}
        # Find the page_content endblock and remove the extra </div> before it
        # This handles the closing of main-content div
        content = re.sub(
            r'</div>\s*</div>\s*({%\s*endblock\s*%})',
            r'</div>\n\1', content
        )
    
    # Remove conflicting sidebar CSS from page_css blocks
    # For recouvrement and library templates that define .sidebar in page_css
    content = re.sub(
        r'/\*\s*[\-]+\s*Sidebar Styles\s*[\-]+\s*\*/.*?/\*\s*Logout Button\s*\*/',
        '/* Sidebar styles removed - handled by base_monecole.html */',
        content, flags=re.DOTALL
    )
    
    # Clean up multiple blank lines
    content = re.sub(r'\n{4,}', '\n\n', content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  FIXED: {filepath}")
        return True
    else:
        print(f"  OK (no changes): {filepath}")
        return False

# Files to fix
templates_to_fix = [
    'evaluation/index_evaluation.html',
    'inscription/index_inscription.html', 
    'enseignement/index_enseignement.html',
    'recouvrement/index_recouvrement.html',
    'library/index_library.html',
]

print("=" * 60)
print("Fixing template layout conflicts...")
print("=" * 60)

fixed_count = 0
for template in templates_to_fix:
    filepath = os.path.join(TEMPLATES_DIR, template)
    if os.path.exists(filepath):
        if fix_template(filepath):
            fixed_count += 1
    else:
        print(f"  SKIP (not found): {filepath}")

print(f"\nFixed {fixed_count} templates")
print("Done!")
