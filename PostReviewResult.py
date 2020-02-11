#!/usr/bin/python3.7
#####Downloading Python bindings for Selenium
#####You can download Python bindings for Selenium from the PyPI page for selenium package.
#####However, a better approach would be to use pip to install the selenium package. 
#####Python 3.6 has pip available in the standard library. Using pip, you can install selenium like this:
#####pip install selenium
#####You may consider using virtualenv to create isolated Python environments. Python 3.6 has pyvenv which is almost the same as virtualenv.
#####Drivers
#####Selenium requires a driver to interface with the chosen browser. 
#####Firefox, for example, requires geckodriver, which needs to be installed before the below examples can be run. 
#####Make sure it’s in your PATH, e. g., place it in /usr/bin or /usr/local/bin.
#####Failure to observe this step will give you an error selenium.common.exceptions.WebDriverException: 
#####Message: ‘geckodriver’ executable needs to be in PATH.
#####Other supported browsers will have their own drivers available. Links to some of the more popular browser drivers follow.
#####Chrome: 	https://sites.google.com/a/chromium.org/chromedriver/downloads
#####Edge: 	https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
#####Firefox: 	https://github.com/mozilla/geckodriver/releases
#####Safari: 	https://webkit.org/blog/6900/webdriver-support-in-safari-10/
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def post_onto_openQA(weburl, postcontent, build, arch):
    driver = webdriver.Firefox()
    login_username = "waynechen55"
    login_password = "CHNBe!j1ngWfcWayne@"
    try:
        driver.get(weburl)
    except Exception as e:
        print (e)
        print ('Can not open ', weburl)
        raise
    else:
        try:
            web_title = WebDriverWait(driver, 60).until(EC.title_contains('openQA'))
        except Exception as e:
            print (e)
            print ('Cand not open openQA group overview page')
            raise
        else:
            print ('openQA group overview webpage ', weburl, ' is available')

        try:
            login_element_locator = "/html/body/nav/div/div/ul[2]/li/a"
            login_element = driver.find_element_by_xpath(login_element_locator)
        except Exception as e:
            print (e)
            print ('Can not find login button')
            raise
        else:
            login_element.click()
            try:
                web_title = WebDriverWait(driver, 600).until(EC.title_contains('SUSE Login'))
            except Exception as e:
                print (e)
                print ('Can not open SUSE Login webpage')
                raise
            else:
                suselogin_username_locator = "//*[@id=\"username\"]"
                suselogin_password_locator = "//*[@id=\"password\"]"
                suselogin_button_locator = "/html/body/div[1]/div/div/div/div/div[1]/div[2]/p/a"
                suselogin_username = WebDriverWait(driver, 600).until(EC.element_to_be_clickable((By.XPATH, suselogin_username_locator)))
                suselogin_username.send_keys(login_username)
                print ('Typed in SUSE login username')
                suselogin_password = WebDriverWait(driver, 600).until(EC.visibility_of_element_located((By.XPATH, suselogin_password_locator)))
                suselogin_password.send_keys(login_password)
                print ('Typed in SUSE login password')
                suselogin_password.send_keys(Keys.ENTER)
                print ('Pressed ENTER key')
                #suseloing_button = WebDriverWait(driver, 600).until(EC.element_to_be_clickable((By.XPATH, suselogin_button_locator)))
                #suselogin_button.click()
                #print ('Clicked SUSE login button')
                time.sleep(10)
                try:
                    web_title = WebDriverWait(driver, 600).until(EC.title_contains('openQA'))
                    loggedin_user_element_locator = "/html/body/nav/div/div/ul[2]/li/a"
                    loggedin_user_element_text = "Logged in as "+login_username
                    WebDriverWait(driver, 600).until(EC.text_to_be_present_in_element((By.XPATH, loggedin_user_element_locator), loggedin_user_element_text))
                except Exception as e:
                    print (e)
                    print ('Submit SUSE login username/password failed')
                    raise
                else:
                    print ('Already logged in as ', login_username)
                    try:
                        write_comment_locator = "//*[@id=\"text\"]"
                        write_comment_element = WebDriverWait(driver, 600).until(EC.element_to_be_clickable((By.XPATH, write_comment_locator)))
                    except Exception as e:
                        print (e)
                        print ('Can not find text input area')
                        raise
                    else:
                        write_comment_element.click()
                        write_comment_element.clear()
                        review_results = open(postcontent, 'r')
                        for eachline in review_results:
                            write_comment_element.send_keys(eachline)
                        review_results.close()
                        try:
                            submit_comment_locator = "//*[@id=\"submitComment\"]"
                            submit_comment_element = WebDriverWait(driver, 600).until(EC.element_to_be_clickable((By.XPATH, submit_comment_locator)))
                        except Exception as e:
                            print (e)
                            print ('Can not find submit comment button')
                            raise
                        else:
                            submit_comment_element.click()
                            time.sleep(10)
                            try:
                                web_title = WebDriverWait(driver, 120).until(EC.title_contains('openQA'))
                            except Exception as e:
                                print (e)
                                print ('openQA webpage is not available after submitting comment')
                                raise
                            else:
                                driver.refresh()
                                try:
                                    submit_comment_locator = "//*[@id=\"submitComment\"]"
                                    submit_comment_element = WebDriverWait(driver, 600).until(EC.element_to_be_clickable((By.XPATH, submit_comment_locator)))
                                except Exception as e:
                                    print (e)
                                    print ('Can not fetch openQA webpage after refresh')
                                    raise
                                else:
                                    try:
                                        comments_locator = "//div[@class=\"media-comment markdown\"]"
                                        comment_elements = driver.find_elements_by_xpath(comments_locator)
                                    except Exception as e:
                                        print (e)
                                        print ('Did not post review result successfully')
                                        raise
                                    else:
                                        post_result_pattern = ".*Build "+build+"\nArch "+arch+".*"
                                        post_result_status = 'failed'
                                        for comment_element in comment_elements:
                                            comment_content = comment_element.text
                                            if (re.match(post_result_pattern, comment_content)):
                                                post_result_status = 'succeeded'
                                                print ("Post review result onto ", weburl, " succeeded")
                                                print (comment_content)
                                                break
                                        if (post_result_status == 'failed'):
                                            print ("Post review result onto ", weburl, " failed")
    finally:
        driver.close()

