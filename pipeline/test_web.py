from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(15000)
    
    # Capture console logs
    logs = []
    page.on('console', lambda msg: logs.append(f'{msg.type}: {msg.text}'))
    page.on('pageerror', lambda err: logs.append(f'PAGEERROR: {err}'))
    
    # Retry navigation
    for attempt in range(3):
        try:
            page.goto('http://localhost:8000/web/index.html')
            break
        except Exception as e:
            print(f'Attempt {attempt+1} failed: {e}')
            time.sleep(2)
    
    page.wait_for_load_state('networkidle', timeout=10000)
    time.sleep(2)  # Give JS time to render
    
    # Take screenshot
    page.screenshot(path=r'C:\Users\grifo\OneDrive\AI\VibeVoding\JHexam\pipeline\output\web_screenshot.png', full_page=True)
    
    # Dump body HTML for inspection
    html = page.content()
    with open(r'C:\Users\grifo\OneDrive\AI\VibeVoding\JHexam\pipeline\output\web_dump.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print('=== Console logs ===')
    for log in logs:
        print(log)
    print('=== Page info ===')
    print('Title:', page.title())
    print('Body length:', len(html))
    print('Nav buttons:', page.locator('.qnav-btn').count())
    print('Quiz content length:', len(page.locator('#quiz').text_content() or ''))
    
    # Navigate to Q4 (has 圖一)
    page.get_by_role('button', name='4', exact=True).click()
    page.wait_for_timeout(1000)
    page.screenshot(path=r'C:\Users\grifo\OneDrive\AI\VibeVoding\JHexam\pipeline\output\web_q4.png', full_page=True)
    print('Q4 figures:', page.locator('.q-figure').count())
    print('Q4 stem:', page.locator('.q-stem').first.text_content()[:80])
    if page.locator('.q-figure img').count():
        print('Q4 figure img src:', page.locator('.q-figure img').first.get_attribute('src'))
    
    # Navigate to a group question (Q43)
    page.get_by_role('button', name='43', exact=True).click()
    page.wait_for_timeout(500)
    print('Q43 type:', page.locator('.q-type').first.text_content())
    if page.locator('.q-group-range').count():
        print('Q43 group range:', page.locator('.q-group-range').first.text_content())
    
    browser.close()
