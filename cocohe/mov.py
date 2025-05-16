from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import urllib.request

# Chromeのオプションを設定
chrome_options = Options()
#chrome_options.add_argument("--headless")  # ヘッドレスモードを使用する場合はこの行を有効に

# WebDriverのパスを設定（バックスラッシュを二重にするか、スラッシュを使用）
webdriver_service = Service('C:/Users/User/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe')  # 例: 'C:/Users/YourUsername/Downloads/chromedriver.exe'

# WebDriverを起動
driver = webdriver.Chrome(service=webdriver_service, options=chrome_options)

# 指定されたURLにアクセス
driver.get('https://lumalabs.ai/dream-machine/creations')

# ページが完全に読み込まれるまで待機（必要に応じて調整）
time.sleep(5)

# Googleでサインインするリンクをクリック
sign_in_with_google_link = driver.find_element(By.XPATH, '//a[contains(@href, "login/google")]')
sign_in_with_google_link.click()

# 新しいタブが開かれるので、そのタブに切り替える
WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
driver.switch_to.window(driver.window_handles[1])

# Googleのサインインページでユーザー名（メールアドレス）を入力して次へボタンをクリック
email = "your-email@gmail.com"  # Googleアカウントのメールアドレス
password = "your-password"  # Googleアカウントのパスワード


# 画像を生成するためのプロンプトのリスト
prompts = [f"Prompt {i+1}" for i in range(30)]  # 例として "Prompt 1", "Prompt 2", ..., "Prompt 30" を使用

# 画像の保存先ディレクトリ
output_dir = 'C:/path/to/save/images/'  # 保存先のディレクトリを指定

for i, prompt in enumerate(prompts):
    # プロンプトを入力

        # プロンプトを入力
    prompt_input = driver.find_element(By.XPATH, '/html/body/div[2]/main/div/div/div[1]/div/div/div[2]/div/textarea')  # 指定されたXPATHを使用
    prompt_input.clear()
    prompt_input.send_keys(prompt)
    
    # 画像生成ボタンをクリック
    generate_button = driver.find_element(By.XPATH, '//button[text()="Generate"]')  # ボタンのテキストを使用して要素を特定
    generate_button.click()


    
    # 画像生成ボタンをクリック
    generate_button = driver.find_element(By.ID, 'generate-button-id')  # 実際の画像生成ボタンのIDを指定
    generate_button.click()
    
    # 画像が生成されるまで待機（適切な時間に調整）
    time.sleep(10)  # 実際の待機時間に調整
    
    # 生成された画像のURLを取得
    image_element = driver.find_element(By.XPATH, 'image-xpath')  # 生成された画像要素のXPATHを指定
    image_url = image_element.get_attribute('src')
    
    # 画像をダウンロードして保存
    image_path = f"{output_dir}/image_{i+1}.png"
    urllib.request.urlretrieve(image_url, image_path)
    print(f"Downloaded {image_path}")
    
    # 次のプロンプトのためにページをリロード
    driver.refresh()
    time.sleep(5)

# ブラウザを閉じる
driver.quit()
