import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    NoAlertPresentException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
#               CẤU HÌNH TÀI KHOẢN
# ==========================================
USERNAME = "108953"
PASSWORD = "nguyenducphuong"

# URL đăng nhập mới của myUDA
LOGIN_URL = "https://sinhvien.donga.edu.vn"
SURVEY_LIST_URL = "https://sinhvien.donga.edu.vn/Khaosat/DanhSachKhaoSat"
FALLBACK_SURVEY_URL = "https://sinhvien.donga.edu.vn/khaosat/index"
WAIT_TIMEOUT = 60

DEFAULT_COMMENT = "Em không có ý kiến gì thêm. Em cảm ơn Thầy/Cô ạ!"


# ==========================================
#           HÀM HỖ TRỢ XỬ LÝ (HELPERS)
# ==========================================
def wait_for_page_and_ajax(driver, timeout=20):
    """
    Đợi trang web nạp xong hoàn toàn:
    - document.readyState == 'complete'
    - Ajax jQuery/Fetch hoàn tất
    - Không còn trạng thái operation-running hoặc loading spinner (.sakura-hud)
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # 1. Đợi document ready
            is_ready = driver.execute_script("return document.readyState") == "complete"
            
            # 2. Đợi jQuery Ajax & UDA operation running kết thúc
            is_ajax_busy = driver.execute_script("""
                try {
                    var jqBusy = (typeof jQuery !== 'undefined') ? (jQuery.active > 0) : false;
                    var udaBusy = (typeof window.isGlobalOperationRunning === 'function') 
                                    ? window.isGlobalOperationRunning() 
                                    : document.body.classList.contains('operation-running');
                    return jqBusy || udaBusy;
                } catch(e) {
                    return false;
                }
            """)
            
            # 3. Đợi sakura-hud (loading spinner riêng của UDA) biến mất
            hud_visible = False
            hud_elements = driver.find_elements(By.CSS_SELECTOR, "#khaosat-list-container .sakura-hud, .sakura-hud")
            for h in hud_elements:
                if h.is_displayed():
                    hud_visible = True
                    break

            if is_ready and not is_ajax_busy and not hud_visible:
                break
        except Exception:
            pass
        time.sleep(0.3)
    time.sleep(0.5)


def safe_click(driver, element):
    """
    Click an toàn, tự động cuộn đến phần tử và fallback dùng JS click nếu bị che khuất
    """
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)
        time.sleep(0.2)
        element.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            return False


def handle_confirm_popups(driver):
    """
    Tự động xử lý tất cả các loại popup xác nhận:
    1. Alert trình duyệt (JavaScript Alert/Confirm)
    2. Modal xác nhận mới của UDA (#globalConfirmModal -> #globalConfirmBtn)
    3. SweetAlert2 (.swal2-confirm)
    """
    # 1. Browser Alert
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        alert.accept()
        print(f"   [Popup] Đã xác nhận browser alert: {alert_text}")
        time.sleep(0.5)
    except NoAlertPresentException:
        pass
    except Exception:
        pass

    # 2. UDA Global Confirm Modal (#globalConfirmModal)
    try:
        confirm_btn = driver.find_element(By.ID, "globalConfirmBtn")
        if confirm_btn.is_displayed() and confirm_btn.is_enabled():
            safe_click(driver, confirm_btn)
            print("   [Popup] Đã bấm 'Đồng ý' trên modal xác nhận.")
            time.sleep(0.5)
    except Exception:
        pass

    # 3. SweetAlert2 Popups
    try:
        swal_buttons = driver.find_elements(By.CSS_SELECTOR, "button.swal2-confirm, .swal2-actions button")
        for btn in swal_buttons:
            if btn.is_displayed() and btn.is_enabled():
                safe_click(driver, btn)
                print("   [Popup] Đã xác nhận popup thông báo (SweetAlert).")
                time.sleep(0.5)
                break
    except Exception:
        pass


# ==========================================
#     TỰ ĐỘNG THỰC HIỆN CÂU HỎI TRONG 1 MÔN
# ==========================================
def fill_survey_form(driver, wait):
    """
    Tự động tích điểm tối đa và điền các câu hỏi trong trang khảo sát
    """
    wait_for_page_and_ajax(driver)

    # 1. Tự động chọn tất cả radio điểm tối đa (value='5' hoặc value='4')
    radios_val5 = driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][value='5']")
    if len(radios_val5) > 0:
        print(f"   -> Tìm thấy {len(radios_val5)} câu hỏi (thang điểm 5). Đang tích chọn...")
        for r in radios_val5:
            try:
                if not r.is_selected():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", r)
                    driver.execute_script("arguments[0].click();", r)
            except Exception:
                try:
                    label = r.find_element(By.XPATH, "ancestor::label")
                    label.click()
                except Exception:
                    pass
    else:
        # Nếu không có value='5', gom nhóm theo name và chọn radio cuối cùng của mỗi nhóm
        print("   -> Tự động tìm tất cả nhóm câu hỏi radio để chọn mức cao nhất...")
        all_radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        groups = {}
        for r in all_radios:
            name = r.get_attribute("name")
            if name:
                groups.setdefault(name, []).append(r)

        for name, r_list in groups.items():
            try:
                # Chọn radio cuối cùng (thường là điểm cao nhất hoặc Rất hài lòng)
                target = r_list[-1]
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
                driver.execute_script("arguments[0].click();", target)
            except Exception:
                pass

    # 2. Điền các ô ý kiến / nhận xét nếu có
    textareas = driver.find_elements(By.TAG_NAME, "textarea")
    for ta in textareas:
        try:
            if ta.is_displayed() and not ta.get_attribute("value"):
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ta)
                ta.clear()
                ta.send_keys(DEFAULT_COMMENT)
                print("   -> Đã điền ý kiến đóng góp.")
        except Exception:
            pass

    time.sleep(0.5)

    # 3. Tìm và nhấn nút Lưu / Hoàn thành
    save_selectors = [
        (By.ID, "button"),
        (By.ID, "btnSave"),
        (By.ID, "btnSubmit"),
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "input[type='submit']"),
        (By.XPATH, "//button[contains(.,'Lưu') or contains(.,'Hoàn thành') or contains(.,'Gửi')]"),
        (By.XPATH, "//input[@type='button' and (contains(@value,'Lưu') or contains(@value,'Gửi'))]"),
        (By.XPATH, "//a[contains(@class,'btn') and (contains(.,'Lưu') or contains(.,'Hoàn thành'))]")
    ]

    save_btn = None
    for by, sel in save_selectors:
        try:
            elements = driver.find_elements(by, sel)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    save_btn = el
                    break
            if save_btn:
                break
        except Exception:
            continue

    if save_btn:
        print("   -> Đang nhấn nút Lưu khảo sát...")
        safe_click(driver, save_btn)
        time.sleep(1)

        # Xử lý các popup xác nhận sau khi bấm Lưu
        for _ in range(3):
            handle_confirm_popups(driver)
            time.sleep(0.6)

        return True
    else:
        print("   ⚠️ Không tìm thấy nút Lưu/Gửi khảo sát trên trang này!")
        return False


# ==========================================
#     QUY TRÌNH TỰ ĐỘNG LÀM TOÀN BỘ KHẢO SÁT
# ==========================================
def do_all_surveys(driver, wait):
    """
    Quét danh sách và lặp qua từng học phần cần khảo sát cho đến khi hết
    """
    completed_count = 0

    while True:
        # Điều hướng về danh sách khảo sát (URL mới)
        current_url = driver.current_url.lower()
        if "danhsachkhaosat" not in current_url:
            print("🔄 Đang chuyển tới trang Danh sách khảo sát...")
            driver.get(SURVEY_LIST_URL)

        # Đợi danh sách nạp xong qua Ajax
        wait_for_page_and_ajax(driver, timeout=25)

        # Tìm các nút làm khảo sát
        # Hỗ trợ cả giao diện mới và cũ: nút link tới /khaosat/thuchien, /Khaosat/ThucHien hoặc có text khảo sát
        survey_buttons = []
        possible_selectors = [
            "a[href*='/khaosat/thuchien' i]",
            "a[href*='/Khaosat/ThucHien' i]",
            "a[href*='thuchien' i]",
            "#khaosat-list-container a.btn-primary",
            "#khaosat-list-container a.btn-success",
            "a.btn.btn-primary[href*='khaosat']"
        ]

        for selector in possible_selectors:
            found = driver.find_elements(By.CSS_SELECTOR, selector)
            for btn in found:
                try:
                    text = btn.text.strip().lower()
                    href = btn.get_attribute("href") or ""
                    # Bỏ qua các nút đã hoàn thành, xem lại, hủy
                    if any(x in text for x in ["xem lại", "đã hoàn thành", "kết quả", "chi tiết"]):
                        continue
                    if btn.is_displayed() and btn not in survey_buttons:
                        survey_buttons.append(btn)
                except Exception:
                    continue
            if survey_buttons:
                break

        if not survey_buttons:
            # Kiểm tra nếu còn text loading hay lỗi
            empty_hud = driver.find_elements(By.CSS_SELECTOR, "#khaosat-list-container .sakura-hud")
            if empty_hud and any(h.is_displayed() for h in empty_hud):
                print("⏳ Danh sách đang tải, chờ thêm một chút...")
                time.sleep(2)
                continue

            print("==================================================")
            print(f"🎉 TẤT CẢ MÔN ĐÃ LÀM XONG! (Tổng cộng hoàn thành: {completed_count} môn)")
            print("==================================================")
            return

        print(f"\n📋 Phát hiện {len(survey_buttons)} môn chưa làm khảo sát. Đang tiến hành...")
        target_btn = survey_buttons[0]

        # Lấy thông tin link môn học
        href = target_btn.get_attribute("href")

        try:
            # Ưu tiên mở trực tiếp href nếu có URL để tránh lỗi bị che nút
            if href and href.startswith("http"):
                driver.get(href)
            else:
                safe_click(driver, target_btn)
        except Exception as e:
            print(f"⚠️ Không thể mở khảo sát: {e}")
            safe_click(driver, target_btn)

        time.sleep(1)

        # Điền và nộp form khảo sát
        success = fill_survey_form(driver, wait)
        if success:
            completed_count += 1
            print(f"✔️ Đã hoàn thành môn thứ {completed_count}!")
        else:
            print("⚠️ Bỏ qua hoặc gặp trục trặc khi lưu môn này.")

        time.sleep(1.5)


# ==========================================
#                   MAIN
# ==========================================
def main():
    print("🚀 Khởi động trình duyệt tự động khảo sát...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    # Tắt thông báo tự động hóa của Chrome
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    try:
        # 1. Mở trang đăng nhập myUDA mới
        print(f"🔑 Đang mở cổng đăng nhập: {LOGIN_URL}...")
        driver.get(LOGIN_URL)

        # Tìm ô tài khoản (hỗ trợ cả hệ thống mới idsv và hệ thống cũ UserName)
        user_selectors = [
            (By.ID, "idsv"),
            (By.NAME, "idsv"),
            (By.ID, "UserName"),
            (By.NAME, "UserName")
        ]
        username_field = None
        for by, sel in user_selectors:
            try:
                el = wait.until(EC.presence_of_element_located((by, sel)))
                if el.is_displayed():
                    username_field = el
                    break
            except Exception:
                continue

        if not username_field:
            raise Exception("Không tìm thấy ô nhập mã sinh viên / tài khoản!")

        # Tìm ô mật khẩu
        pass_selectors = [
            (By.ID, "password"),
            (By.NAME, "password"),
            (By.ID, "Password"),
            (By.NAME, "Password")
        ]
        password_field = None
        for by, sel in pass_selectors:
            try:
                el = driver.find_element(by, sel)
                if el.is_displayed():
                    password_field = el
                    break
            except Exception:
                continue

        if not password_field:
            raise Exception("Không tìm thấy ô nhập mật khẩu!")

        print(f"📝 Đang điền tài khoản: {USERNAME}...")
        username_field.clear()
        username_field.send_keys(USERNAME)
        password_field.clear()
        password_field.send_keys(PASSWORD)

        # Nút đăng nhập mới là button.btn-login hoặc submit qua phím ENTER
        time.sleep(0.3)
        login_btn = None
        try:
            login_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-login, button[type='submit']")
        except Exception:
            pass

        if login_btn and login_btn.is_displayed():
            safe_click(driver, login_btn)
        else:
            password_field.send_keys(Keys.ENTER)

        print("⏳ Đang chờ đăng nhập...")
        time.sleep(2.5)

        # 2. Điều hướng thẳng tới trang khảo sát học phần mới
        print("📂 Đang mở trang Khảo sát học phần...")
        driver.get(SURVEY_LIST_URL)
        time.sleep(1)

        # Kiểm tra nếu trang mới không khả dụng thì thử fallback qua menu hoặc URL cũ
        if "DanhSachKhaoSat" not in driver.current_url and "khaosat" not in driver.current_url.lower():
            try:
                menu_btn = driver.find_element(By.CSS_SELECTOR, "a[href='#sidebarKhaosat'], a[data-bs-target='#sidebarKhaosat']")
                safe_click(driver, menu_btn)
                time.sleep(0.5)
                sub_link = driver.find_element(By.CSS_SELECTOR, "a[href*='/Khaosat/DanhSachKhaoSat']")
                safe_click(driver, sub_link)
            except Exception:
                driver.get(FALLBACK_SURVEY_URL)

        # 3. Thực hiện toàn bộ khảo sát
        do_all_surveys(driver, wait)

    except Exception as e:
        print("❌ Lỗi trong quá trình chạy:", e)

    finally:
        print("🏁 Đang kết thúc chương trình...")
        time.sleep(3)
        driver.quit()


if __name__ == "__main__":
    main()
