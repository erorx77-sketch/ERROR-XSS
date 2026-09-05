import time
import threading
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException


print("""


    ███████╗██████╗ ██████╗  ██████╗ ██████╗       ██╗  ██╗███████╗███████╗
    ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗      ╚██╗██╔╝██╔════╝██╔════╝
    █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝       ╚███╔╝ ███████╗███████╗
    ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗       ██╔██╗ ╚════██║╚════██║
    ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║      ██╔╝ ██╗███████║███████║
    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝      ╚═╝  ╚═╝╚══════╝╚══════╝

""")


# 1. Configuration
target_url = input("WEB : ")  # Replace with your target URL
wordlist_file = "xss_list.txt"

driver = webdriver.Chrome()
driver.get(target_url)

print("\n" + "="*70)
print("[STEP 1] Click inside the TARGET INPUT box (where lines should be tested).")
print("[STEP 2] Press [ENTER] in this terminal to lock the target input.")
print("="*70 + "\n")

def handle_alerts():
    """Dismisses any unexpected JavaScript alert dialogs."""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        alert.accept()
        return alert_text
    except NoAlertPresentException:
        return None

# Lock target input element via XPath
target_element = None
target_xpath = ""

while True:
    try:
        handle_alerts()
        active_el = driver.switch_to.active_element
        if active_el.tag_name.lower() in ['input', 'textarea']:
            elem_name = active_el.get_attribute("name")
            elem_id = active_el.get_attribute("id")
            
            if elem_id:
                target_xpath = f"//*[@id='{elem_id}']"
            elif elem_name:
                target_xpath = f"//*[@name='{elem_name}']"
            else:
                target_xpath = f"//{active_el.tag_name}[1]"
                
            print(f"[+] Locked target input with path: {target_xpath}")
            break
    except Exception:
        pass
    time.sleep(0.5)

# Save baseline text safely after handling initial alerts
driver.get(target_url)
time.sleep(2)
handle_alerts()

try:
    initial_page_text = driver.find_element("tag name", "body").text
except UnexpectedAlertPresentException:
    handle_alerts()
    initial_page_text = driver.find_element("tag name", "body").text

saved_extra_inputs = {}
pause_requested = False

def listen_for_pause():
    global pause_requested
    while True:
        input()
        pause_requested = True

threading.Thread(target=listen_for_pause, daemon=True).start()

def get_filled_extra_inputs():
    extra_data = {}
    inputs = driver.find_elements("tag name", "input") + driver.find_elements("tag name", "textarea")
    for elem in inputs:
        try:
            val = elem.get_attribute("value")
            elem_name = elem.get_attribute("name") or elem.get_attribute("id")
            if val and elem_name:
                extra_data[elem_name] = val
        except Exception:
            pass
    return extra_data

def fill_extra_inputs(saved_data):
    for name_or_id, val in saved_data.items():
        try:
            elem = driver.find_element("name", name_or_id)
        except Exception:
            try:
                elem = driver.find_element("id", name_or_id)
            except Exception:
                elem = None
                
        if elem:
            try:
                elem.clear()
                elem.send_keys(val)
            except Exception:
                pass

def submit_form():
    try:
        submit_btn = driver.find_element("xpath", "//button[@type='submit'] | //input[@type='submit']")
        submit_btn.click()
    except Exception:
        pass

try:
    with open(wordlist_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    print("\n Tip: Press ENTER in terminal anytime to pause & fill static extra fields.")

    for line_number, text_to_type in enumerate(lines, 1):
        
        if pause_requested:
            print("\n" + "="*60)
            print(" [PAUSED] Execution paused.")
            print(" Fill static extra fields in browser.")
            print(" Press [ENTER] in terminal to save fields and resume testing...")
            print("="*60)
            input()
            
            saved_extra_inputs = get_filled_extra_inputs()
            print(f"[+] Saved {len(saved_extra_inputs)} extra field(s) permanently.")
            pause_requested = False

        print(f"\n--------------------------------------------------")
        print(f"[*] [{line_number}/{len(lines)}] Testing target line: '{text_to_type}'")

        # Reload page
        driver.get(target_url)
        time.sleep(1.5)
        handle_alerts()

        # Refill saved extra fields
        if saved_extra_inputs:
            fill_extra_inputs(saved_extra_inputs)

        # Insert payload into target element
        try:
            target_el = driver.find_element("xpath", target_xpath)
            target_el.clear()
            target_el.send_keys(text_to_type)
        except Exception as e:
            print(f"[-] Could not locate target element: {e}")
            continue

        submit_form()
        time.sleep(2)

        # Check for triggered alert or text change
        triggered_alert = handle_alerts()
        
        try:
            current_page_text = driver.find_element("tag name", "body").text.strip()
        except UnexpectedAlertPresentException:
            triggered_alert = handle_alerts()
            current_page_text = driver.find_element("tag name", "body").text.strip()

        if triggered_alert:
            print(f"🚨 [ALERT]: JavaScript Alert Triggered! Content: '{triggered_alert}' with line: '{text_to_type}'")

        elif "Missing parameter" in current_page_text:
            print("[i] Normal response received ('Missing parameter'). Moving to next...")

        elif current_page_text != initial_page_text:
            print(f"🚨 [ALERT]: Response changed after testing line: '{text_to_type}'")
            print(f"    Preview: {current_page_text[:120]}...")
            initial_page_text = current_page_text

        else:
            print("[i] No change detected.")

except FileNotFoundError:
    print(f"[-] Error: File '{wordlist_file}' not found.")
except Exception as e:
    print(f"[-] Error occurred: {e}")

print("\n[+] Testing completed for all lines.")