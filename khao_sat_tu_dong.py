from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

USERNAME = "108953"
PASSWORD = "nguyenducphuong"

LOGIN_URL = "https://sinhvien.donga.edu.vn/Sinh-vien/dang-nhap?ReturnUrl=%2f"
WAIT_TIMEOUT = 180



def safe_click(driver, element):
    try:
        element.click()
        return True
    except:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.3)
        try:
            element.click()
            return True
        except:
            return False


# ==========================================
#   HÀM MỚI: TỰ ĐỘNG LÀM TẤT CẢ KHẢO SÁT
# ==========================================
def do_all_survey(driver, wait):
    while True:
        wait.until(lambda current_driver: current_driver.execute_script("return document.readyState") == "complete")

        # 1) Lấy danh sách tất cả nút "Chọn khảo sát"
        buttons = driver.find_elements(By.CSS_SELECTOR, "a.btn.btn-primary[href*='/khaosat/thuchien']")


        if len(buttons) == 0:
            print("🎉 Không còn môn nào cần khảo sát.")
            return

        # lấy môn đầu tiên
        btn = buttons[0]

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.3)
        btn.click()

        # 2) Tick radio value=5
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='radio'][value='5']")))
        radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][value='5']")

        for r in radios:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", r)
                r.click()
            except:
                try:
                    label = r.find_element(By.XPATH, "ancestor::label")
                    label.click()
                except:
                    pass

        # 3) Nhấn nút Lưu
        save_btn = wait.until(EC.element_to_be_clickable((By.ID, "button")))
        safe_click(driver, save_btn)

        print("✔️ Đã hoàn thành 1 môn!")

        time.sleep(1)

        # 4) Quay lại danh sách khảo sát để làm môn tiếp theo
        driver.get("https://sinhvien.donga.edu.vn/khaosat/index")
        time.sleep(1)


# ==========================================
#                   MAIN
# ==========================================
def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    try:
        # Login
        driver.get(LOGIN_URL)

        username_field = wait.until(EC.presence_of_element_located((By.ID, "UserName")))
        password_field = wait.until(EC.presence_of_element_located((By.ID, "Password")))

        username_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD)
        password_field.send_keys(Keys.ENTER)

        # Vào khảo sát học phần
        ks_menu = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(.,'Khảo sát') and contains(@class,'dropdown-toggle')]")
            )
        )
        safe_click(driver, ks_menu)

        ks_hp = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[@href='/khaosat/index' or contains(., 'KS học phần')]")
            )
        )
        safe_click(driver, ks_hp)

        # Gọi hàm TỰ ĐỘNG LÀM HẾT KHẢO SÁT
        do_all_survey(driver, wait)

        print("🎉🎉🎉 TẤT CẢ MÔN ĐÃ LÀM XONG!")

    except Exception as e:
        print("❌ Lỗi:", e)

    finally:
        time.sleep(2)
        driver.quit()


if __name__ == "__main__":
    main()
#& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m pip install selenium
#& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" .\khao_sat_tu_dong.py