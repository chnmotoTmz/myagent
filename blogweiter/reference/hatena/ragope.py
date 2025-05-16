from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
import time
import pdb

def access_website_click_button_and_enter_prompt(url, button_id, textarea_testid, prompt, wait_time=60):
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--allow-running-insecure-content')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(wait_time)
    
    print(f"URLにアクセスします: {url}")
    driver.get(url)
    print("URLにアクセスしました。")

        # ページの読み込みを待つ
    time.sleep(10)

        # ボタンが表示されるまで待機
    button = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.ID, button_id))
    )

    text_analysis_button = WebDriverWait(driver, 10).until(
      EC.element_to_be_clickable((By.ID, "component-28-button"))
  )

    text_analysis_button.click()
    print("「Text Analysis」ボタンをクリックしました。")

        # data-testid属性を使ってテキストエリア要素を探す
    text_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[data-testid='textbox']"))
    )
    
    pdb.set_trace()

    text_input.send_keys("入力したいテキスト")
    print("テキストを入力しました。")

            # aria-label属性を使って入力フィールド要素を探す
    top_n_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[aria-label='Top N']"))
    )
    
    top_n_input.send_keys("1")
    print("「Top N」フィールドに1を入力しました。")

  
    # IDでボタン要素を探す
    submit_button = WebDriverWait(driver, 10).until(
      EC.element_to_be_clickable((By.ID, "component-34"))
  )
    submit_button.click()
    print("「Submit」ボタンをクリックしました。")

# テキストエリアのテキストを取得

    # data-testid属性を使ってテキストエリア要素を探す
    result_textarea = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[data-testid='textbox']"))
    )
    result_text = result_textarea.get_attribute("value")
    print("取得したテキスト: ", result_text)
    return result_text


# 関数の使用例
url = "http://chanmoto.synology.me:22356/"
button_id = "component-28-button"
textarea_testid = "textbox"
prompt = "ここにプロンプトを入れる"

result = access_website_click_button_and_enter_prompt(url, button_id, textarea_testid, prompt)

if result:
    print("操作が成功しました。")
else:
    print("操作が失敗しました。")