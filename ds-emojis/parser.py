import json
import logging
import random
import time

import httplib2 as httplib2
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


def start_parse():
    logger = init_logger("Emojis")
    logger.info(f"Start parsing...")

    url = "https://unicode.org/emoji/charts/full-emoji-list.html"
    chromedriver_path = "C:\\Users\\User\\WebstormProjects\\admin-bot.jaristo-cyber-room.ru\\ds-emojis\\chromedriver.exe"

    options = Options()
    # options.add_argument('--headless')
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1024,600')
    options.add_argument(
        "user-agent=Mozilla / 5.0(Windows NT 10.0; Win64; x64) AppleWebKit / 537.36(KHTML, like Gecko) Chrome "
        "/ 104.0.0.0 Safari / 537.36")

    try:
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
        driver.implicitly_wait(10)
        driver.get(url=url)
        logger.info("Selenium launched the browser...")
    except Exception as e:
        logger.error("Selenium FAILED to launch browser!")
        logger.exception(e)


    try:
        with open("emojis.json") as f:
            old_result = json.load(f)
        result = []
        i = 0
        logger.info("The required parameters are initialized. Data parsing begins...")
        emoji_list = driver.find_element(By.XPATH, "/html/body/div[3]/table/tbody")
        emoji_tr = emoji_list.find_elements(By.TAG_NAME, "tr")
        logger.info(f"Total: {len(emoji_tr)}")
        for tr in emoji_tr:
            try:
                emoji_uni = tr.find_element(By.CLASS_NAME, "chars").text
                emoji_name = tr.find_element(By.CLASS_NAME, "name").text
                json_str = {"unicode": emoji_uni, "name": emoji_name}
                result.append(json_str)
                i += 1
                logger.info(f"{i} - Added...")
            except:
                continue

        # logger.info(f"Element list received. Total: {len(emojis)}")
        # for emoji in emojis:
        #     emoji_img = emoji.find_element(By.TAG_NAME, "img")
        #     emoji_uni = emoji_img.get_attribute("alt")
        #     emoji_src = emoji_img.get_attribute("src")
        #     emoji_svg = f"https://twemoji.maxcdn.com/v/12.1.4/{emoji_src}"
        #     download_img(emoji_svg, i)
        #     json_str = {"unicode": emoji_uni, "svg_path": f"ds-emojis/svg/{i}.svg"}
        #     result.append(json_str)
        #     i += 1
        #     logger.info(f"{i} - Added...")
        save_json(result)
    except Exception as e:
        logger.exception(e)
    finally:
        driver.close()
        driver.quit()
        logger.info("Program execution has been stopped!")


def save_json(result):
    path = "new_emojis.json"
    with open(path, 'w') as outfile:
        json.dump(result, outfile)


def download_img(img, i):
    h = httplib2.Http('.cache')
    response, content = h.request(img)
    out = open(f"svg/{i}.svg", 'wb+')
    out.write(content)
    out.close()


def init_logger(name):
    path_logs = "parser.log"
    logger = logging.getLogger(name)
    FORMAT = '%(asctime)s :: %(name)s:%(lineno)s :: %(levelname)s :: %(message)s'
    logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(FORMAT))
    sh.setLevel(logging.DEBUG)
    fh = logging.FileHandler(filename=path_logs)
    fh.setFormatter(logging.Formatter(FORMAT))
    fh.setLevel(logging.DEBUG)
    logger.addHandler(sh)
    logger.addHandler(fh)
    logger.debug("Logger was initialized.")
    return logger


# get_p2p_okx("btc")

if __name__ == '__main__':
    start_parse()

