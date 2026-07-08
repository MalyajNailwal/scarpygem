from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
import base64
import re
from PIL import Image
import pytesseract
import time
import os


def select_category(driver, category):
    element = Select(driver.find_element(By.ID, 'buyer_category'))
    element.select_by_visible_text(category)
    print(f'Selected Category: {category}')

def select_date_range(driver, from_date, to_date):
    from_date_element = driver.find_element(By.ID, 'from_date_contract_search1')
    to_date_element = driver.find_element(By.ID, 'to_date_contract_search1')

    driver.execute_script("arguments[0].removeAttribute('readonly')", from_date_element)
    driver.execute_script("arguments[0].removeAttribute('readonly')", to_date_element)

    from_date_element.clear()
    from_date_element.send_keys(from_date)
    to_date_element.clear()
    to_date_element.send_keys(to_date)

    print(f'Selected Date Range: {from_date} to {to_date}')

def extract_captcha(driver, img_id, captcha_dir="captcha"):
    os.makedirs(captcha_dir, exist_ok=True)
    try:
        captcha_img = driver.find_element(By.ID, img_id)
        img_src = captcha_img.get_attribute("src")
        match = re.search(r'base64,(.*)', img_src)
        if match:
            base64_string = match.group(1)
            image_data = base64.b64decode(base64_string)
            captcha_path = os.path.join(captcha_dir, "captcha.jpg")
            with open(captcha_path, "wb") as img_file:
                img_file.write(image_data)
        else:
            print("Failed to read Captcha!")
            return False
        return True
    except Exception as e:
        print(f"Error extracting Captcha: {e}")
        return False

def read_captcha(captcha_dir="captcha"):
    try:
        image = Image.open(os.path.join(captcha_dir, "captcha.jpg"))
        text = pytesseract.image_to_string(image)
        captcha = text.replace(" ", "").strip()
        return captcha
    except Exception as e:
        print(f"Error reading Captcha: {e}")
        return ""

def refresh_captcha(driver, img_id, captcha_dir="captcha"):
    try:
        print("Refreshing Captcha...")
        refresh_button = driver.find_element(By.XPATH, "//a[contains(@onclick, 'loadCap1')]")
        refresh_button.click()
        time.sleep(2)
        extract_captcha(driver, img_id, captcha_dir)
    except Exception as e:
        print(f"Error refreshing Captcha: {e}")

def enter_captcha(driver, captcha_code, img_id, captcha_dir="captcha", max_retries=10):
    for attempt in range(max_retries):
        extract_captcha(driver, img_id, captcha_dir)
        captcha = read_captcha(captcha_dir)
        if not captcha:
            print(f"Captcha OCR returned empty, attempt {attempt+1}/{max_retries}")
            refresh_captcha(driver, img_id, captcha_dir)
            continue

        cap_input = driver.find_element(By.ID, captcha_code)
        cap_input.clear()
        cap_input.send_keys(captcha)

        search_button = driver.find_element(By.ID, "searchlocation1")
        driver.execute_script("arguments[0].click();", search_button)
        time.sleep(1)

        try:
            error = driver.find_element(By.ID, "pcaptcha_code1").text.strip()
            if error:
                print(f"Captcha wrong, attempt {attempt+1}/{max_retries}")
                refresh_captcha(driver, img_id, captcha_dir)
            else:
                print("Captcha accepted! Loading Documents.")
                return True
        except Exception:
            print("Captcha accepted! Loading Documents.")
            return True

    print(f"Failed after {max_retries} captcha attempts")
    return False

def enter_captcha_and_download(driver, captcha_code):
    try:
        h_captcha_value = driver.find_element(By.ID, "h_captcha").get_attribute("value")
        cap_input = driver.find_element(By.ID, captcha_code)
        cap_input.send_keys(h_captcha_value)
        search_button = driver.find_element(By.ID, "modelsbt")
        search_button.click()
        time.sleep(1)
        download_button = driver.find_element(By.ID, "dwnbtn")
        download_button.click()
        print("Download triggered.")
        return True
    except Exception as e:
        print(f"Error downloading document: {e}")
        return False

def get_document_info(driver):
    documents = driver.find_elements(By.CLASS_NAME, "border.block")
    doc_list = []
    for i, doc in enumerate(documents):
        try:
            link = doc.find_element(By.TAG_NAME, "a")
            text = doc.text.strip().split('\n')[0] if doc.text.strip() else f"Document_{i+1}"
            doc_list.append({"index": i, "text": text, "element_index": i})
        except Exception:
            doc_list.append({"index": i, "text": f"Document_{i+1}", "element_index": i})
    return doc_list
