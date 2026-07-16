from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(20000)
    
    logs = []
    page.on('console', lambda msg: logs.append(f'{msg.type}: {msg.text}'))
    page.on('pageerror', lambda err: logs.append(f'PAGEERROR: {err}'))
    page.on('requestfailed', lambda req: logs.append(f'REQFAIL: {req.url} - {req.failure}'))
    
    page.goto('http://localhost:8000/web/index.html')
    page.wait_for_load_state('networkidle', timeout=15000)
    time.sleep(3)
    
    # Check actual state
    print('=== Console / errors ===')
    for log in logs:
        print(log)
    
    print()
    print('=== DOM state ===')
    print('Title:', repr(page.title()))
    print('year-badge:', repr(page.locator('#year-badge').text_content()))
    print('qnav children:', page.locator('#qnav').locator('*').count())
    print('quiz innerHTML length:', len(page.locator('#quiz').inner_html() or ''))
    print('quiz text:', repr(page.locator('#quiz').text_content()[:200] if page.locator('#quiz').count() else 'NO QUIZ ELEMENT'))
    print('q-counter:', repr(page.locator('#q-counter').text_content()))
    
    # Dump full body
    with open(r'C:\Users\grifo\OneDrive\AI\VibeVoding\JHexam\pipeline\output\debug_dump.html', 'w', encoding='utf-8') as f:
        f.write(page.content())
    
    page.screenshot(path=r'C:\Users\grifo\OneDrive\AI\VibeVoding\JHexam\pipeline\output\debug.png', full_page=True)
    print()
    print('Screenshot + dump saved')
    
    browser.close()
