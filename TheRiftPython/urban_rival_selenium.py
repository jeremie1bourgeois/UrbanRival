from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
import base64
import os
import shutil
import time
import random
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.safari.options import Options as SafariOptions

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from selenium.webdriver.firefox.options import Options
from selenium.webdriver.chrome.service import Service

from itertools import combinations
import numpy as np
import itertools
from itertools import permutations


# Configure Firefox options to modify headers
firefox_options = Options()
firefox_options.add_argument("--headless")
firefox_options.add_argument("--disable-extensions")
firefox_options.add_argument("--disable-gpu")
firefox_options.add_argument("--no-sandbox")
firefox_options.add_argument("--disable-dev-shm-usage")
firefox_options.set_preference("dom.webdriver.enabled", False)
firefox_options.set_preference('useAutomationExtension', False)
firefox_options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")

# Set up the Firefox driver with the modified options
service = Service(executable_path="geckodriver.exe")
driver = webdriver.Firefox(service=service, options=firefox_options)



def wait_for(xpath, timeout = 5):
	try:
		WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
	except TimeoutException as e:
		print(e)
		exit(1)

# driver.get('https://www.urban-rivals.com/game/play/webgl/')
driver.get('https://www.chess.com/login_and_go?returnUrl=https://www.chess.com/')


wait_for("//*[@id=\"username\"]")
# driver.find_element(By.XPATH, "//*[@id=\"username\"]").send_keys("damien.brgs92@gmail.com")
# driver.find_element(By.XPATH, "//*[@id=\"password\"]").send_keys("Bourgeois92")

driver.find_element(By.XPATH, "/html/body/div[1]/div/main/div/div/div[2]/a[2]").click()

exit(0)
# driver.find_element(By.XPATH, "//input[@name='password']").send_keys("Bourgeois92")
wait = WebDriverWait(driver, 10)
login_element = wait.until(EC.element_to_be_clickable((By.NAME, "login")))
login_element.send_keys("damien.brgs92@gmail.com")
# Sélectionnez la canvas
canvas = driver.find_element_by_id('unity-canvas')

# # Exécutez un script JavaScript pour extraire les données de la canvas en utilisant html2canvas
# script = "return new Promise(resolve => {" \
#          "html2canvas(document.querySelector('#unity-canvas')).then(canvas => {" \
#          "resolve(canvas.toDataURL('image/png').substring(22));" \
#          "});" \
#          "});"
# data = driver.execute_script(script)

# # Convertir les données en image
# img_data = base64.b64decode(data)
# with open('canvas.png', 'wb') as f:
#     f.write(img_data)

# # Fermez le navigateur
# driver.close()