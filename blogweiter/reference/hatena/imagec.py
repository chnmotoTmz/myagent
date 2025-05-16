import os
import time
import hashlib
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

# Load environment variables
load_dotenv()

# Get email and password from environment variables
email = os.getenv('EMAIL')
password = os.getenv('PASSWORD')

def generate_image_folder_hash(prompt):
    """Generates a hash based on the prompt to use as the folder name."""
    return hashlib.sha256(prompt.encode()).hexdigest()


def generate_and_save_image(prompt):
    """
    Generates an image based on the given prompt using Bing Image Creator,
    saves the first generated image to an encrypted folder,
    and returns the path to the saved image.

    Args:
        prompt (str): The prompt to generate the image from.

    Returns:
        str: The path to the saved image.
    """

    # Set up the WebDriver (Chrome in this example)
    driver = webdriver.Chrome()

    try:
        # Navigate to the ImageCreator website
        driver.get("https://www.bing.com/images/create#")

# Find the textarea element and enter the prompt
        prompt_input = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "sb_form_q"))
)
        prompt_input.send_keys(prompt)

# Find and click the create button
        create_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.ID, "create_btn_c"))
)
        create_button.click()

# Find the email input field and enter the email
        email_input = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.NAME, "loginfmt"))
)
        email_input.send_keys(email)

# Find and click the "Next" button
        next_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.ID, "idSIButton9"))
)
        next_button.click()

    # Wait for the password field to be visible and enter the password
        password_input = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "i0118"))
)
        password_input.send_keys(password)

# Find and click the sign-in button
        signin_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.ID, "idSIButton9"))
)
        signin_button.click()

# Wait for the "Stay signed in?" page and click "Yes" (はい)
        yes_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, "//button[@id='acceptButton'][contains(text(), 'はい')]"))
)
        yes_button.click()


# Wait for the images to load
        WebDriverWait(driver, 30).until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "img.mimg"))
)

# Find all image elements
        image_elements = driver.find_elements(By.CSS_SELECTOR, "img.mimg")

        # ... (rest of the code to log in and download images)

        # Generate folder name from prompt hash
        folder_name = generate_image_folder_hash(prompt)
        image_folder = os.path.join("generated_images", folder_name)

                # Create the folder if it doesn't exist
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)

        # Download and save only the first 4 images
        for i, img in enumerate(image_elements[:4], start=1):
            image_url = img.get_attribute("src")
            response = requests.get(image_url)
            if response.status_code == 200:
                image_filename = f"image_{i}.jpg"
                image_path = os.path.join(image_folder, image_filename)
                with open(image_path, "wb") as file:
                    file.write(response.content)
                print(f"Image {i} saved successfully to {image_path}.")
            else:
                print(f"Failed to download image {i}.")

        return image_folder

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    finally:
        # Close the browser
        driver.quit()

# Example usage
#image_folder = generate_and_save_image("a cute cat wearing sunglasses")
#image_folder = generate_and_save_image("a cute bear wearing sunglasses")
#image_folder = generate_and_save_image("a cute mouse wearing sunglasses")
#image_folder = generate_and_save_image("a cute dog wearing sunglasses")

