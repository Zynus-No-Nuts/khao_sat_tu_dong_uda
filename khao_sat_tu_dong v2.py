import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    NoAlertPresentException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
#               CẤU HÌNH TÀI KHOẢN
# ==========================================
USERNAME = "108953"
PASSWORD = "nguyenducphuong"

LOGIN_URL = "https://sinhvien.donga.edu.vn"
SURVEY_LIST_URL = "https://sinhvien.donga.edu.vn/Khaosat/DanhSachKhaoSat"
FALLBACK_SURVEY_URL = "https://sinhvien.donga.edu.vn/khaosat/index"
WAIT_TIMEOUT = 30

DEFAULT_COMMENT = "Em không có ý kiến gì thêm. Em cảm ơn Thầy/Cô ạ!"


# ==========================================
#     HÀM ĐỢI THÔNG MINH (POLLING NHANH)
# ==========================================
def wait_for_ajax_done(driver, timeout=8):
    """
    Polling nhanh (50ms) để đợi Ajax và quá trình xử lý của trang kết thúc,
    không dùng time.sleep cứng gây chậm trễ.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            busy = driver.execute_script("""
                try {
                    var jqBusy = (typeof jQuery !== 'undefined') && (jQuery.active > 0);
                    var udaBusy = (typeof window.isGlobalOperationRunning === 'function') 
                                    ? window.isGlobalOperationRunning() 
                                    : document.body.classList.contains('operation-running');
                    var hudBusy = document.querySelector('#khaosat-list-container .sakura-hud') !== null;
                    return jqBusy || udaBusy || hudBusy;
                } catch(e) {
                    return false;
                }
            """)
            if not busy:
                return True
        except Exception:
            pass
        time.sleep(0.05)
    return False


def wait_for_survey_list(driver, timeout=12):
    """
    Đợi danh sách học phần nạp xong nội dung từ Ajax
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status = driver.execute_script("""
                var container = document.getElementById('khaosat-list-container');
                if (!container) return 'not_found';
                if (container.querySelector('.sakura-hud')) return 'loading';
                // Kiểm tra xem đã có bảng hoặc nút khảo sát chưa
                var links = container.querySelectorAll("a[href*='thuchien' i], a.btn, table");
                if (links.length > 0) return 'ready';
                // Hoặc thông báo không có môn
                if (container.innerText.includes('không') || container.children.length > 0) return 'ready';
                return 'waiting';
            """)
            if status == 'ready':
                return True
        except Exception:
            pass
        time.sleep(0.08)
    return False


# ==========================================
#   SIÊU TỐC: ĐIỀN FORM BẰNG 1 LỆNH JAVASCRIPT
# ==========================================
def turbo_fill_and_submit(driver, default_comment=DEFAULT_COMMENT):
    """
    Thực hiện toàn bộ:
    1. Override confirm/alert để tự động đồng ý
    2. Tự động chọn tất cả radio điểm tối đa (thang 5 hoặc mức cao nhất)
    3. Điền textarea ý kiến đóng góp
    4. Tìm và bấm nút Lưu
    5. Kích hoạt auto-click modal xác nhận (#globalConfirmBtn / SweetAlert)
    Tất cả chạy trực tiếp trong DOM trình duyệt (< 50ms)
    """
    js_code = """
    const comment = arguments[0];
    
    // 1. Tự động bypass alert và confirm của trình duyệt
    window.confirm = function() { return true; };
    window.alert = function() { return true; };

    let totalAnswered = 0;

    // 2. Tự động tick radio điểm tối đa (value='5' hoặc option cao nhất)
    const radios5 = document.querySelectorAll("input[type='radio'][value='5']");
    if (radios5.length > 0) {
        radios5.forEach(r => {
            r.checked = true;
            r.dispatchEvent(new Event('change', { bubbles: true }));
            r.dispatchEvent(new Event('click', { bubbles: true }));
            totalAnswered++;
        });
    } else {
        // Fallback: nhóm theo name và chọn radio cuối cùng (mức cao nhất)
        const groups = {};
        document.querySelectorAll("input[type='radio']").forEach(r => {
            if (r.name) {
                if (!groups[r.name]) groups[r.name] = [];
                groups[r.name].push(r);
            }
        });
        for (const name in groups) {
            const list = groups[name];
            const target = list[list.length - 1];
            target.checked = true;
            target.dispatchEvent(new Event('change', { bubbles: true }));
            target.dispatchEvent(new Event('click', { bubbles: true }));
            totalAnswered++;
        }
    }

    // 3. Điền các ô ý kiến / nhận xét nếu có
    document.querySelectorAll("textarea").forEach(ta => {
        if (!ta.value || ta.value.trim() === '') {
            ta.value = comment;
            ta.dispatchEvent(new Event('input', { bubbles: true }));
            ta.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });

    // 4. Tìm và nhấn nút Lưu/Gửi
    let saveBtn = document.getElementById('button') || 
                  document.getElementById('btnSave') || 
                  document.getElementById('btnSubmit') ||
                  document.querySelector("button[type='submit']") ||
                  document.querySelector("input[type='submit']");

    if (!saveBtn) {
        // Tìm theo text nút
        const buttons = document.querySelectorAll("button, a.btn, input[type='button']");
        for (let b of buttons) {
            const t = (b.innerText || b.value || '').toLowerCase();
            if (t.includes('lưu') || t.includes('hoàn thành') || t.includes('gửi')) {
                saveBtn = b;
                break;
            }
        }
    }

    let clicked = false;
    if (saveBtn) {
        saveBtn.click();
        clicked = true;
    }

    // 5. Tự động click modal xác nhận ngay khi xuất hiện
    let checks = 0;
    const modalWatcher = setInterval(() => {
        checks++;
        const confirmBtn = document.getElementById('globalConfirmBtn');
        if (confirmBtn && confirmBtn.offsetParent !== null) {
            confirmBtn.click();
            clearInterval(modalWatcher);
        }
        const swalBtn = document.querySelector('.swal2-confirm');
        if (swalBtn && swalBtn.offsetParent !== null) {
            swalBtn.click();
            clearInterval(modalWatcher);
        }
        if (checks > 30) clearInterval(modalWatcher);
    }, 50);

    return { totalAnswered: totalAnswered, clicked: clicked };
    """

    try:
        res = driver.execute_script(js_code, default_comment)
        return res
    except Exception as e:
        return {"error": str(e), "totalAnswered": 0, "clicked": False}


def fast_confirm_popups(driver):
    """
    Xác nhận nhanh các popup còn sót lại (nếu có)
    """
    # Browser Alert
    try:
        alert = driver.switch_to.alert
        alert.accept()
    except NoAlertPresentException:
        pass
    except Exception:
        pass

    # Modal / SweetAlert
    try:
        driver.execute_script("""
            const c = document.getElementById('globalConfirmBtn');
            if (c) c.click();
            const s = document.querySelector('.swal2-confirm');
            if (s) s.click();
        """)
    except Exception:
        pass


# ==========================================
#     QUY TRÌNH TỐI ƯU HÓA KHẢO SÁT
# ==========================================
def extract_all_survey_links(driver):
    """
    Trích xuất toàn bộ danh sách URL môn học cần khảo sát trong 1 lần duy nhất
    """
    js_extract = """
    const results = [];
    const elements = document.querySelectorAll(
        "a[href*='/khaosat/thuchien' i], a[href*='/Khaosat/ThucHien' i], a[href*='thuchien' i], #khaosat-list-container a.btn"
    );

    elements.forEach(el => {
        const text = (el.innerText || "").trim().toLowerCase();
        const href = el.href;
        if (!href) return;
        
        // Loại bỏ các nút xem lại hoặc đã hoàn thành
        if (text.includes('xem lại') || text.includes('đã hoàn thành') || text.includes('kết quả')) {
            return;
        }

        if (!results.includes(href)) {
            results.push(href);
        }
    });

    return results;
    """
    try:
        return driver.execute_script(js_extract) or []
    except Exception:
        return []


def do_turbo_surveys(driver):
    """
    Quy trình khảo sát tốc độ cao:
    - Quét lấy toàn bộ link khảo sát ngay từ đầu
    - Duyệt qua từng link bằng driver.get trực tiếp (không reload danh sách sau mỗi môn)
    - Tự động điền + nộp chỉ trong 1 lần thực thi JS
    - Kiểm tra lại 1 lần cuối để đảm bảo không sót môn
    """
    total_completed = 0
    round_no = 1

    while True:
        # Chuyển tới trang danh sách nếu chưa ở đó
        if "danhsachkhaosat" not in driver.current_url.lower():
            driver.get(SURVEY_LIST_URL)

        # Đợi danh sách hiển thị
        wait_for_survey_list(driver)
        wait_for_ajax_done(driver)

        survey_links = extract_all_survey_links(driver)

        if not survey_links:
            # Kiểm tra nếu còn hud loading
            time.sleep(0.5)
            survey_links = extract_all_survey_links(driver)

        if not survey_links:
            print("\n==================================================")
            print(f"🎉 TẤT CẢ MÔN ĐÃ HOÀN THÀNH! (Tổng số môn đã làm: {total_completed})")
            print("==================================================")
            break

        print(f"\n📋 [Lượt {round_no}] Phát hiện {len(survey_links)} môn cần làm khảo sát.")

        for idx, link in enumerate(survey_links, start=1):
            t_start = time.time()
            print(f"⚡ [{idx}/{len(survey_links)}] Đang xử lý: {link}")

            try:
                # Mở trực tiếp trang làm khảo sát
                driver.get(link)

                # Chờ form xuất hiện (nhanh, tối đa 5s)
                form_ready = False
                for _ in range(30):
                    ready = driver.execute_script(
                        "return document.querySelectorAll(\"input[type='radio'], textarea, button\").length > 0;"
                    )
                    if ready:
                        form_ready = True
                        break
                    time.sleep(0.08)

                if not form_ready:
                    print("   ⚠️ Không tìm thấy câu hỏi, chuyển môn tiếp theo.")
                    continue

                # Điền và nộp bài tức thì bằng Turbo JS
                res = turbo_fill_and_submit(driver)
                answered = res.get('totalAnswered', 0)
                clicked = res.get('clicked', False)

                # Chờ popup xác nhận & phản hồi lưu
                time.sleep(0.4)
                fast_confirm_popups(driver)
                time.sleep(0.3)

                t_cost = round(time.time() - t_start, 2)
                if clicked or answered > 0:
                    total_completed += 1
                    print(f"   ✔️ Đã trả lời {answered} câu & nộp thành công! (Mất {t_cost}s)")
                else:
                    print(f"   ⚠️ Đã xử lý (mất {t_cost}s)")

            except Exception as e:
                print(f"   ❌ Lỗi xử lý môn này: {e}")

        round_no += 1
        # Sau khi duyệt hết danh sách link, quay lại trang danh sách để xác nhận hoàn tất
        driver.get(SURVEY_LIST_URL)


# ==========================================
#                   MAIN
# ==========================================
def main():
    print("🚀 Khởi động trình duyệt tốc độ cao (Turbo Mode)...")

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Chiến lược tải trang Eager: tương tác ngay khi DOM Interactive, không đợi asset phụ
    options.page_load_strategy = "eager"

    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    try:
        t_all_start = time.time()

        # 1. Đăng nhập siêu tốc
        print(f"🔑 Đang mở cổng đăng nhập: {LOGIN_URL}...")
        driver.get(LOGIN_URL)

        # Chờ ô tài khoản xuất hiện
        user_field = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#idsv, input[name='idsv'], #UserName"))
        )

        # Tự động điền và submit bằng JS cực nhanh (1 round-trip)
        print(f"📝 Đăng nhập tài khoản: {USERNAME}...")
        driver.execute_script("""
            const u = arguments[0];
            const p = arguments[1];
            const userInp = document.getElementById('idsv') || document.querySelector("input[name='idsv']") || document.getElementById('UserName');
            const passInp = document.getElementById('password') || document.querySelector("input[name='password']") || document.getElementById('Password');
            if (userInp && passInp) {
                userInp.value = u;
                passInp.value = p;
                userInp.dispatchEvent(new Event('input', {bubbles: true}));
                passInp.dispatchEvent(new Event('input', {bubbles: true}));
                const btn = document.querySelector('button.btn-login') || document.querySelector("button[type='submit']");
                if (btn) btn.click();
                else passInp.form.submit();
            }
        """, USERNAME, PASSWORD)

        # Đợi đăng nhập hoàn tất (URL thay đổi hoặc qua trang khác)
        for _ in range(40):
            cur = driver.current_url.lower()
            if "login" not in cur and cur.rstrip('/') != LOGIN_URL.rstrip('/'):
                break
            time.sleep(0.1)

        # 2. Điều hướng thẳng tới trang khảo sát học phần mới
        print("📂 Đang mở trang Khảo sát học phần...")
        driver.get(SURVEY_LIST_URL)

        # 3. Chạy quy trình khảo sát siêu tốc
        do_turbo_surveys(driver)

        total_time = round(time.time() - t_all_start, 2)
        print(f"\n⏱️ Tổng thời gian thực hiện: {total_time} giây!")

    except Exception as e:
        print("❌ Lỗi trong quá trình chạy:", e)

    finally:
        print("🏁 Đang đóng trình duyệt...")
        time.sleep(1.5)
        driver.quit()


if __name__ == "__main__":
    main()
